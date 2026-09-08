"""A scheduler's advisory selection must not outlive account erasure."""
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update
from mozhna import scheduler
from mozhna.db import Job, Schedule, Record, LoginSession, OwnerState
from mozhna.main import create_app
from test_api import PASSWORD, client, plan


def due_schedule(client):
    p = client.post('/api/v1/plans',json=plan()).json()
    client.patch('/api/v1/plans/'+p['id'],json={'expected_version':1,'status':'active'})
    scheduled = client.post('/api/v1/schedules',json={'plan_id':p['id']}).json()
    with client.app.state.factory.begin() as db:
        db.execute(update(Schedule).where(Schedule.id == scheduled['id'])
            .values(next_due=time.time()-10))
    return scheduled


def assert_stale_schedule_cannot_recreate_data(client, monkeypatch):
    due_schedule(client)
    owner = client.get('/api/v1/auth/me').json()['user']['id']
    selected, proceed = Event(), Event()
    actual_lock = scheduler.lock_owner

    def pause_after_selection(db, owner_id):
        selected.set()
        assert proceed.wait(5), 'Erase did not complete'
        return actual_lock(db,owner_id)

    monkeypatch.setattr(scheduler,'lock_owner',pause_after_selection)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(scheduler.tick,client.app.state.factory)
        try:
            assert selected.wait(5), 'Scheduler did not select the candidate'
            assert client.request('DELETE','/api/v1/data',json={'confirmation':'DELETE'}).status_code == 200
        finally:
            proceed.set()
        pending.result(timeout=5)
    with client.app.state.factory() as db:
        assert db.scalar(select(Schedule).where(Schedule.owner_id == owner)) is None
        assert db.scalar(select(Job).where(Job.owner_id == owner)) is None
        assert db.scalar(select(Record).where(Record.owner_id == owner)) is None


def test_stale_schedule_selection_cannot_recreate_erased_data(client, monkeypatch):
    assert_stale_schedule_cannot_recreate_data(client,monkeypatch)


def test_two_scheduler_processes_enqueue_one_occurrence(client):
    due_schedule(client)
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _:scheduler.tick(client.app.state.factory),range(2)))
    with client.app.state.factory() as db:
        assert len(db.scalars(select(Job)).all()) == 1


@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'),reason='Disposable PostgreSQL not configured')
def test_postgres_stale_schedule_selection_after_erase(monkeypatch):
    owner = 'scheduler-test-'+uuid.uuid4().hex
    monkeypatch.setenv('MOZHNA_OWNER_ID',owner)
    monkeypatch.setenv('MOZHNA_PASSWORD',PASSWORD)
    monkeypatch.setenv('MOZHNA_ENV','development')
    monkeypatch.delenv('PUBLIC_ORIGIN',raising=False)
    monkeypatch.delenv('RENDER_EXTERNAL_URL',raising=False)
    app = create_app(os.environ['TEST_DATABASE_URL'])
    try:
        with TestClient(app) as c:
            response = c.post('/api/v1/auth/login',json={'password':PASSWORD})
            assert response.status_code == 200
            c.headers['X-CSRF-Token'] = response.json()['csrf_token']
            assert_stale_schedule_cannot_recreate_data(c,monkeypatch)
    finally:
        with app.state.factory.begin() as db:
            for model in (Job,Schedule,Record,LoginSession,OwnerState):
                db.execute(delete(model).where(model.owner_id == owner))
        app.state.engine.dispose()
