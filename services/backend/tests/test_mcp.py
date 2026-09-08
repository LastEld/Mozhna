"""A real MCP SDK client over loopback HTTP, with no external model calls."""
import asyncio
import socket
import threading
import time

import httpx
import httpx2
import uvicorn
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mozhna.main import create_app
from mozhna.db import Record


def test_remote_mcp_requires_token_and_only_exposes_owner_reads(tmp_path, monkeypatch):
    token = 'synthetic-mcp-token-for-tests-only-12345678'
    monkeypatch.setenv('MOZHNA_MCP_TOKEN', token)
    monkeypatch.setenv('MOZHNA_ENV', 'development')
    monkeypatch.delenv('PUBLIC_ORIGIN', raising=False)
    app = create_app('sqlite:///'+str(tmp_path/'mcp.db'))
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    url = f'http://127.0.0.1:{sock.getsockname()[1]}/mcp/'
    server = uvicorn.Server(uvicorn.Config(app, log_level='error'))
    thread = threading.Thread(target=server.run, kwargs={'sockets':[sock]}, daemon=True)
    thread.start()
    try:
        for _ in range(100):
            if server.started:
                break
            time.sleep(.02)
        assert server.started
        with app.state.factory.begin() as db:
            db.add(Record(id='other-plan',owner_id='different-owner',kind='plan',data={'title':'Private'}))
        with httpx.Client(trust_env=False) as http:
            assert http.post(url).status_code == 401
            assert http.post(url, headers={'Authorization':'Bearer wrong'}).status_code == 401

        async def exercise():
            async with httpx2.AsyncClient(trust_env=False, headers={'Authorization':'Bearer '+token}) as http:
                async with Client(streamable_http_client(url,http_client=http), mode='legacy') as client:
                    listed = await client.list_tools()
                    assert {t.name for t in listed.tools} == {'money_status','can_spend','get_plans','get_jobs'}
                    money = await client.call_tool('money_status', {})
                    assert not money.is_error
                    assert 'UNKNOWN' in str(money)
                    plans = await client.call_tool('get_plans', {})
                    assert not plans.is_error and 'Private' not in str(plans)
                    bad = await client.call_tool('can_spend', {'amount_minor':-1})
                    assert bad.is_error
        asyncio.run(exercise())
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        sock.close()
    assert not thread.is_alive()
