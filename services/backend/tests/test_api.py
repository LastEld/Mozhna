from datetime import datetime, timezone
import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from mozhna.main import create_app
from mozhna.db import Job, Schedule
from mozhna.jobs import claim, run_once
from mozhna.scheduler import tick

PASSWORD = 'synthetic-test-password-only'

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('MOZHNA_PASSWORD', PASSWORD)
    monkeypatch.setenv('MOZHNA_ENV', 'development')
    monkeypatch.delenv('PUBLIC_ORIGIN', raising=False)
    monkeypatch.delenv('MOZHNA_ALLOW_PAID_INFERENCE', raising=False)
    app = create_app('sqlite:///'+str(tmp_path/'test.db'))
    with TestClient(app) as c:
        response = c.post('/api/v1/auth/login', json={'password': PASSWORD})
        assert response.status_code == 200
        c.headers['X-CSRF-Token'] = response.json()['csrf_token']
        yield c


def snapshot():
    return {'balance_minor':100000,'reserve_minor':20000,'goal_minor':5000,
            'living_budget_minor':10000,'currency':'EUR','horizon_days':30,
            'commitments':[{'id':'rent','label':'Rent','amount_minor':60000,'due_date':datetime.now(timezone.utc).date().isoformat()}],
            'incomes':[], 'as_of':datetime.now(timezone.utc).isoformat()}


def plan():
    return {'title':'Juice','need':'One portion','baseline_minor':150,
            'alternative_minor':50,'frequency_per_month':20,'setup_cost_minor':0,'currency':'EUR'}


def test_auth_csrf_origin_and_logout(client):
    assert client.get('/api/v1/snapshot').headers['cache-control'] == 'no-store'
    token = client.headers.pop('X-CSRF-Token')
    assert client.put('/api/v1/snapshot',json={'expected_version':0,'snapshot':snapshot()}).status_code == 403
    client.headers['X-CSRF-Token'] = token
    assert client.post('/api/v1/simulate',json={'amount_minor':100},headers={'Origin':'https://attacker.invalid'}).status_code == 403
    assert client.post('/api/v1/auth/logout').status_code == 200
    assert client.get('/api/v1/snapshot').status_code == 401


def test_snapshot_version_simulation_and_persistence(client):
    saved = client.put('/api/v1/snapshot',json={'expected_version':0,'snapshot':snapshot()})
    assert saved.status_code == 200, saved.text
    assert saved.json()['calculation']['planned_limit_minor'] == 5000
    assert client.put('/api/v1/snapshot',json={'expected_version':0,'snapshot':snapshot()}).status_code == 409
    assert client.post('/api/v1/simulate',json={'amount_minor':7000}).json()['decision'] == 'CAN_WITH_TRADEOFF'
    assert client.get('/api/v1/snapshot').json()['snapshot']['balance_minor'] == 100000
    assert client.post('/api/v1/simulate',json={'amount_minor':1.1}).status_code == 422


def test_plan_accept_observe_reject_version(client):
    p = client.post('/api/v1/plans',json=plan()).json()
    assert p['scenario_savings_minor'] == 2000
    observation = {'amount_minor':50,'date':'2026-09-07','note':'same portion'}
    assert client.post('/api/v1/plans/'+p['id']+'/observations',json=observation).status_code == 409
    active = client.patch('/api/v1/plans/'+p['id'],json={'expected_version':1,'status':'active'}).json()
    assert active['version'] == 2
    assert client.patch('/api/v1/plans/'+p['id'],json={'expected_version':1,'status':'rejected'}).status_code == 409
    assert client.post('/api/v1/plans/'+p['id']+'/observations',json=observation).json()['observations'][0]['amount_minor'] == 50


def test_csv_is_idempotent_and_does_not_add_to_balance(client):
    client.put('/api/v1/snapshot',json={'expected_version':0,'snapshot':snapshot()})
    text='date,description,amount_minor,external_id\n2026-09-07,Juice,-150,one\n2026-09-07,Juice,-150,two\n'
    assert client.post('/api/v1/transactions/import',json={'csv_text':text}).json()['added'] == 2
    assert client.post('/api/v1/transactions/import',json={'csv_text':text}).json()['skipped'] == 2
    assert client.get('/api/v1/snapshot').json()['snapshot']['balance_minor'] == 100000
    assert client.post('/api/v1/transactions/import',json={'csv_text':text.replace('-150','-1.50')}).status_code == 422


def test_durable_job_idempotency_resume_cancel(client):
    body={'kind':'compare_plan','provider':'manual','payload':plan(),'idempotency_key':'one'}
    first=client.post('/api/v1/jobs',json=body)
    assert first.status_code == 202, first.text
    job=first.json()
    assert client.post('/api/v1/jobs',json=body).json()['id'] == job['id']
    assert client.post('/api/v1/jobs',json={**body,'payload':{**plan(),'title':'Other'}}).status_code == 409
    assert claim(client.app.state.factory)[0] == job['id']
    # Simulate worker crash: saved lease is expired; a fresh process claims it.
    with client.app.state.factory.begin() as db:
        db.execute(update(Job).where(Job.id == job['id']).values(lease_until=time.time()-1))
    assert run_once(client.app.state.factory)
    done=client.get('/api/v1/jobs/'+job['id']).json()
    assert done['status'] == 'succeeded'
    assert done['result']['monthly_savings_minor'] == 2000
    assert done['attempts'] == 2
    queued=client.post('/api/v1/jobs',json={**body,'idempotency_key':'two'}).json()
    assert client.post('/api/v1/jobs/'+queued['id']+'/cancel').json()['status']=='canceled'
    assert not run_once(client.app.state.factory)


def test_delete_cancels_jobs_sessions_and_schedules(client):
    client.put('/api/v1/snapshot',json={'expected_version':0,'snapshot':snapshot()})
    p=client.post('/api/v1/plans',json=plan()).json()
    client.patch('/api/v1/plans/'+p['id'],json={'expected_version':1,'status':'active'})
    client.post('/api/v1/schedules',json={'plan_id':p['id']})
    assert len(client.get('/api/v1/export').json()['records']) == 2
    assert client.delete('/api/v1/data').status_code == 422
    assert client.request('DELETE','/api/v1/data',json={'confirmation':'DELETE'}).status_code == 200
    assert client.get('/api/v1/export').status_code == 401
    with client.app.state.factory() as db:
        assert db.scalar(select(Schedule)) is None


def test_interval_schedule_coalesces_and_is_not_session_dependent(client):
    p=client.post('/api/v1/plans',json=plan()).json()
    client.patch('/api/v1/plans/'+p['id'],json={'expected_version':1,'status':'active'})
    s=client.post('/api/v1/schedules',json={'plan_id':p['id'],'interval_hours':24}).json()
    with client.app.state.factory.begin() as db:
        db.execute(update(Schedule).where(Schedule.id == s['id']).values(next_due=time.time()-100000))
    client.post('/api/v1/auth/logout')
    tick(client.app.state.factory)
    tick(client.app.state.factory)
    with client.app.state.factory() as db:
        assert len(db.scalars(select(Job)).all()) == 1
    assert run_once(client.app.state.factory)


def test_unconfigured_llm_is_not_a_fake_success(client):
    r=client.post('/api/v1/jobs',json={'kind':'draft_application','provider':'anthropic',
        'payload':{'profile_facts':'Python','job_description':'Role'},'idempotency_key':'draft'})
    assert r.status_code == 409


def test_cross_owner_ids_are_inaccessible(client,monkeypatch):
    p=client.post('/api/v1/plans',json=plan()).json()
    monkeypatch.setenv('MOZHNA_OWNER_ID','another-owner')
    other_app=create_app(str(client.app.state.engine.url))
    with TestClient(other_app) as other:
        login=other.post('/api/v1/auth/login',json={'password':PASSWORD}).json()
        other.headers['X-CSRF-Token']=login['csrf_token']
        assert other.get('/api/v1/plans').json()['items'] == []
        assert other.patch('/api/v1/plans/'+p['id'],json={'expected_version':1,'status':'active'}).status_code == 404


def test_production_fails_without_secrets(monkeypatch):
    monkeypatch.setenv('MOZHNA_ENV','production')
    monkeypatch.delenv('MOZHNA_PASSWORD',raising=False)
    with pytest.raises(RuntimeError):
        create_app('sqlite://')
