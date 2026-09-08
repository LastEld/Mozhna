import os
import subprocess
import time
import uuid
import pytest
from sqlalchemy import delete
from sqlalchemy.engine import make_url
from mozhna.db import Base, Job, Schedule, LoginSession, Record, connect
from mozhna.jobs import run_once
from mozhna.recovery import quarantine

def seed(factory, key):
    with factory.begin() as db:
        db.add(Record(id=key,owner_id=key,kind='snapshot',data={'balance_minor':100000}))
        db.add(Job(id=key,owner_id=key,idempotency_key=key,kind='income_search',provider='manual',payload={'role':'tester'}))
        db.add(LoginSession(token_hash=key,owner_id=key,csrf='synthetic',expires_at=time.time()+1000))
        db.add(Schedule(id=key,owner_id=key,plan_id='synthetic-plan',interval_hours=24,next_due=time.time()))

def verify(factory, key):
    first = quarantine(factory)
    assert first['quarantined_jobs'] >= 1
    assert not run_once(factory)
    assert quarantine(factory) == {'quarantined_jobs':0,'removed_schedules':0,'revoked_sessions':0}
    with factory() as db:
        assert db.get(Record,key).data['balance_minor'] == 100000
        assert db.get(Job,key).status == 'canceled'
        assert db.get(LoginSession,key) is None
        assert db.get(Schedule,key) is None

def test_recovery_preserves_finances_without_reviving_execution(tmp_path):
    engine, factory = connect('sqlite:///'+str(tmp_path/'restore.db'))
    Base.metadata.create_all(engine)
    seed(factory, 'restore-proof')
    verify(factory, 'restore-proof')
    engine.dispose()

@pytest.mark.skipif(not (os.getenv('PG_CONTAINER_ID') and os.getenv('TEST_DATABASE_URL')),
                    reason='Disposable PostgreSQL container not configured')
def test_actual_postgres_dump_restore_and_quarantine():
    # CI-provided service is disposable; generated DB names never target user DBs.
    source = make_url(os.environ['TEST_DATABASE_URL'])
    container = os.environ['PG_CONTAINER_ID']
    restored_name = 'mozhna_restore_'+uuid.uuid4().hex
    key = uuid.uuid4().hex
    engine, factory = connect(source.render_as_string(hide_password=False))
    restored_engine = None
    created = False
    def docker(*args, **kwargs):
        return subprocess.run(['docker','exec','-i',container,*args],check=True,capture_output=True,**kwargs)
    try:
        seed(factory,key)
        backup = docker('pg_dump','-U',source.username,'-d',source.database,'-Fc').stdout
        docker('createdb','-U',source.username,restored_name)
        created = True
        docker('pg_restore','-U',source.username,'-d',restored_name,'--no-owner',input=backup)
        restored_engine, restored_factory = connect(source.set(database=restored_name).render_as_string(hide_password=False))
        verify(restored_factory,key)
    finally:
        if restored_engine:
            restored_engine.dispose()
        if created:
            docker('dropdb','-U',source.username,restored_name)
        with factory.begin() as db:
            for model in (Schedule,Job,LoginSession,Record):
                db.execute(delete(model).where(model.owner_id == key))
        engine.dispose()
