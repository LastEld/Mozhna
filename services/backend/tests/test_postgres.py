"""Run against an isolated disposable PostgreSQL DB, configured by CI."""
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import delete, select, update
from mozhna.db import Job, connect
from mozhna.jobs import claim, run_once

@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Disposable PostgreSQL not configured')
def test_postgres_concurrent_claim_and_restart():
    engine, factory = connect(os.environ['TEST_DATABASE_URL'])
    job_id = uuid.uuid4().hex
    # This DB belongs solely to this CI test; claims may take any queued owner job.
    with factory.begin() as db:
        db.add(Job(id=job_id,owner_id='test-owner',idempotency_key=job_id,
            kind='compare_plan',provider='manual',payload={'title':'Test','baseline_minor':150,
                'alternative_minor':50,'frequency_per_month':20,'setup_cost_minor':0}))
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            claimed = list(pool.map(lambda _:claim(factory), range(2)))
        assert sum(item is not None for item in claimed) == 1
        with factory.begin() as db:
            db.execute(update(Job).where(Job.id==job_id).values(lease_until=time.time()-1))
        assert run_once(factory)
        with factory() as db:
            item = db.get(Job, job_id)
            assert item.status == 'succeeded' and item.attempts == 2
            assert item.result['monthly_savings_minor'] == 2000
    finally:
        with factory.begin() as db:
            db.execute(delete(Job).where(Job.id==job_id))
        engine.dispose()


@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Disposable PostgreSQL not configured')
def test_postgres_login_budget_and_erase_race(monkeypatch):
    from threading import Event
    from fastapi import Request
    from fastapi.testclient import TestClient
    from mozhna.main import create_app
    from mozhna.db import LoginSession, OwnerState, Record
    from test_api import PASSWORD, plan

    owner = 'auth-test-'+uuid.uuid4().hex
    url = os.environ['TEST_DATABASE_URL']
    monkeypatch.setenv('MOZHNA_OWNER_ID',owner)
    monkeypatch.setenv('MOZHNA_PASSWORD',PASSWORD)
    monkeypatch.setenv('MOZHNA_ENV','development')
    monkeypatch.delenv('PUBLIC_ORIGIN',raising=False)
    monkeypatch.delenv('RENDER_EXTERNAL_URL',raising=False)
    first_app, second_app = create_app(url), create_app(url)
    try:
        with TestClient(first_app) as first, TestClient(second_app) as second:
            for c in (first, second):
                response = c.post('/api/v1/auth/login',json={'password':PASSWORD})
                assert response.status_code == 200
                c.headers['X-CSRF-Token'] = response.json()['csrf_token']
            with ThreadPoolExecutor(max_workers=6) as pool:
                responses = list(pool.map(lambda n: (first if n % 2 else second).post(
                    '/api/v1/auth/login',json={'password':'wrong'}).status_code, range(12)))
            assert responses.count(401) == 8 and responses.count(429) == 4
            route = next(r for r in first_app.routes if getattr(r,'path','') == '/api/v1/plans'
                and 'POST' in getattr(r,'methods',set()))
            authenticate = route.dependant.dependencies[0].call
            authenticated, proceed = Event(), Event()

            def pause(request: Request):
                auth = authenticate(request)
                authenticated.set()
                assert proceed.wait(5)
                return auth

            first_app.dependency_overrides[authenticate] = pause
            try:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    pending = pool.submit(first.post,'/api/v1/plans',json=plan())
                    assert authenticated.wait(5)
                    assert second.request('DELETE','/api/v1/data',json={'confirmation':'DELETE'}).status_code == 200
                    proceed.set()
                    assert pending.result(timeout=5).status_code == 401
                with first_app.state.factory() as db:
                    assert db.scalar(select(Record).where(Record.owner_id == owner)) is None
                    assert db.scalar(select(LoginSession).where(LoginSession.owner_id == owner)) is None
            finally:
                proceed.set()
                first_app.dependency_overrides.clear()
    finally:
        with first_app.state.factory.begin() as db:
            db.execute(delete(Record).where(Record.owner_id == owner))
            db.execute(delete(LoginSession).where(LoginSession.owner_id == owner))
            db.execute(delete(OwnerState).where(OwnerState.owner_id == owner))
        first_app.state.engine.dispose()
        second_app.state.engine.dispose()
