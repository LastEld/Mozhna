import uuid
from mozhna.db import Base, Job, connect
from mozhna.jobs import run_once

def test_cancellation_during_execution_cannot_be_overwritten(tmp_path, monkeypatch):
    engine, factory = connect('sqlite:///'+str(tmp_path/'cancel.db'))
    Base.metadata.create_all(engine)
    job_id = uuid.uuid4().hex
    with factory.begin() as db:
        db.add(Job(id=job_id,owner_id='owner',idempotency_key='cancel',kind='income_search',
                   provider='manual',payload={'role':'tester'}))
    def cancel_while_running(job):
        with factory.begin() as db:
            item = db.get(Job, job.id)
            item.status = 'canceled'
            item.lease_token = None
        return {'summary':'Late result must not be saved'}
    monkeypatch.setattr('mozhna.jobs.execute', cancel_while_running)
    assert run_once(factory)
    with factory() as db:
        item = db.get(Job, job_id)
        assert item.status == 'canceled'
        assert item.result is None
    engine.dispose()

def test_worker_rejects_unsafe_aggregate_money(tmp_path):
    engine, factory = connect('sqlite:///'+str(tmp_path/'overflow.db'))
    Base.metadata.create_all(engine)
    job_id = uuid.uuid4().hex
    with factory.begin() as db:
        db.add(Job(id=job_id,owner_id='owner',idempotency_key='overflow',kind='compare_plan',
                   provider='manual',payload={'title':'Overflow','baseline_minor':2**53-1,
                       'alternative_minor':0,'frequency_per_month':2}))
    assert run_once(factory)
    with factory() as db:
        item = db.get(Job, job_id)
        assert item.status == 'failed' and item.result is None
        assert 'unsafe_scenario_amount' in item.error
    engine.dispose()
