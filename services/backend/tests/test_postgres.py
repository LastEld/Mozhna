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
