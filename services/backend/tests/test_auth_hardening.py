"""Regressions for durable auth boundaries, revocation races, and readiness."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
import time

import pytest
from alembic import command
from alembic.config import Config
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from mozhna.db import OwnerState, Record
from mozhna.main import create_app
from test_api import PASSWORD, client, plan


def test_login_budget_shared_across_processes_and_restart(client):
    url = str(client.app.state.engine.url)
    with TestClient(create_app(url)) as second:
        for n in range(8):
            c = client if n % 2 else second
            assert c.post('/api/v1/auth/login', json={'password':'wrong'},
                headers={'X-Forwarded-For':f'192.0.2.{n}'}).status_code == 401
    with TestClient(create_app(url)) as restarted:
        blocked = restarted.post('/api/v1/auth/login',json={'password':PASSWORD})
        assert blocked.status_code == 429
        assert 0 < int(blocked.headers['Retry-After']) <= 301
        with restarted.app.state.factory.begin() as db:
            db.execute(update(OwnerState).values(window_started=time.time()-301))
        assert restarted.post('/api/v1/auth/login',json={'password':PASSWORD}).status_code == 200


def test_parallel_failed_logins_cannot_lose_attempts(client):
    url = str(client.app.state.engine.url)
    with TestClient(create_app(url)) as second:
        with ThreadPoolExecutor(max_workers=8) as pool:
            responses = list(pool.map(lambda n: (client if n % 2 else second).post(
                '/api/v1/auth/login',json={'password':'wrong'}).status_code, range(12)))
    assert responses.count(401) == 8
    assert responses.count(429) == 4
    with client.app.state.factory() as db:
        assert db.get(OwnerState, 'owner').login_failures == 8


@pytest.mark.parametrize('revoke', ['erase', 'logout'])
def test_authenticated_request_cannot_write_after_revocation(client, revoke):
    # Pause after the dependency has accepted the cookie. Revoke from another
    # request, then resume the already-authenticated writer.
    route = next(r for r in client.app.routes if getattr(r, 'path', '') == '/api/v1/plans'
        and 'POST' in getattr(r, 'methods', set()))
    authenticate = route.dependant.dependencies[0].call
    authenticated, proceed = Event(), Event()

    def pause_auth(request: Request):
        result = authenticate(request)
        if request.headers.get('X-Test-Pause'):
            authenticated.set()
            assert proceed.wait(5), 'Revocation did not complete'
        return result

    client.app.dependency_overrides[authenticate] = pause_auth
    cookies = dict(client.cookies)
    csrf = client.headers['X-CSRF-Token']
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(client.post, '/api/v1/plans', json=plan(),
                headers={'X-Test-Pause':'yes'})
            assert authenticated.wait(5), 'Write request did not authenticate'
            if revoke == 'erase':
                response = client.request('DELETE','/api/v1/data',json={'confirmation':'DELETE'})
            else:
                response = client.post('/api/v1/auth/logout')
            assert response.status_code == 200
            proceed.set()
            assert pending.result(timeout=5).status_code == 401
        with client.app.state.factory() as db:
            assert db.scalar(select(Record).where(Record.kind == 'plan')) is None
        # Even retaining the original token and CSRF cannot recreate data.
        client.cookies.update(cookies)
        assert client.post('/api/v1/plans',json=plan(),headers={'X-CSRF-Token':csrf}).status_code == 401
    finally:
        proceed.set()
        client.app.dependency_overrides.clear()


def test_session_from_other_configured_owner_is_rejected(client, monkeypatch):
    monkeypatch.setenv('MOZHNA_OWNER_ID','other-owner')
    with TestClient(create_app(str(client.app.state.engine.url))) as second:
        second.cookies.update(dict(client.cookies))
        assert second.get('/api/v1/auth/me').status_code == 401


def test_readiness_requires_schema_and_upgrade_preserves_data(tmp_path, monkeypatch):
    url = 'sqlite:///'+str(tmp_path/'migration.db')
    monkeypatch.setenv('DATABASE_URL',url)
    monkeypatch.setenv('MOZHNA_ENV','production')
    monkeypatch.setenv('MOZHNA_PASSWORD',PASSWORD)
    monkeypatch.setenv('PUBLIC_ORIGIN','https://mozhna.example')
    backend = Path(__file__).resolve().parents[1]
    config = Config(str(backend/'alembic.ini'))
    config.set_main_option('script_location',str(backend/'migrations'))
    with TestClient(create_app(url),base_url='https://mozhna.example') as c:
        assert c.get('/healthz').status_code == 503
        command.upgrade(config,'0001')
        with c.app.state.factory.begin() as db:
            db.add(Record(id='preserved',owner_id='owner',kind='transaction',data={'synthetic':True}))
        assert c.get('/healthz').status_code == 503
        command.upgrade(config,'head')
        assert c.get('/healthz').status_code == 200
        with c.app.state.factory() as db:
            assert db.get(Record,'preserved').data == {'synthetic':True}
        login = c.post('/api/v1/auth/login',json={'password':PASSWORD})
        assert login.status_code == 200
        assert 'Secure' in login.headers['set-cookie']
        assert 'HttpOnly' in login.headers['set-cookie']
        command.downgrade(config,'0001')
        assert c.get('/healthz').status_code == 503


@pytest.mark.parametrize('origin', ['https://', 'https://example.org/path',
    'https://user:password@example.org', 'https://example.org?x=1',
    'https://example.org#fragment', 'https://example.org:wrong'])
def test_production_rejects_malformed_origin(monkeypatch, origin):
    monkeypatch.setenv('MOZHNA_ENV','production')
    monkeypatch.setenv('MOZHNA_PASSWORD',PASSWORD)
    monkeypatch.setenv('PUBLIC_ORIGIN',origin)
    with pytest.raises(RuntimeError, match='valid HTTPS PUBLIC_ORIGIN'):
        create_app('sqlite://')


@pytest.mark.parametrize('path', ['/api/v1/auth/login', '/mcp/'])
def test_chunked_body_limit_runs_before_json_parser(path):
    import asyncio
    from mozhna.main import RequestBodyLimit
    called = False
    replies = []
    chunks = iter([{'type':'http.request','body':b'a'*6,'more_body':True},
                   {'type':'http.request','body':b'b'*6,'more_body':False}])

    async def parser(scope, receive, send):
        nonlocal called
        called = True

    async def receive():
        return next(chunks)

    async def send(message):
        replies.append(message)

    asyncio.run(RequestBodyLimit(parser,max_bytes=10)(
        {'type':'http','path':path},receive,send))
    assert not called
    assert replies[0]['status'] == 413
