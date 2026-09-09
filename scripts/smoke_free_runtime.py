"""CI-only synthetic proof of the native Free topology and restart persistence."""
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.error import URLError
from urllib.request import Request, urlopen
import uuid

if os.getenv('CI') != 'true' or not os.getenv('TEST_DATABASE_URL'):
    raise SystemExit('Requires CI=true and an isolated TEST_DATABASE_URL')
root = Path(__file__).resolve().parents[1]
env = {**os.environ, 'DATABASE_URL': os.environ['TEST_DATABASE_URL'],
       'MOZHNA_ENV':'production', 'PUBLIC_ORIGIN':'https://mozhna.test',
       'MOZHNA_PASSWORD':'synthetic-ci-password', 'MOZHNA_OWNER_ID':'free-smoke-'+uuid.uuid4().hex,
       'MOZHNA_ALLOW_PAID_INFERENCE':'false', 'MOZHNA_MCP_TOKEN':'', 'PORT':'8001'}
base = 'http://127.0.0.1:8001'

def request(path, body=None, cookie='', csrf=''):
    headers = {'Content-Type':'application/json', 'Cookie':cookie, 'X-CSRF-Token':csrf}
    with urlopen(Request(base+path, data=None if body is None else json.dumps(body).encode(),
                         headers=headers), timeout=3) as response:
        return json.load(response), response.headers

def start():
    process = subprocess.Popen(['bash','scripts/render_start.sh'],cwd=root,env=env)
    try:
        deadline = time.monotonic()+30
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise AssertionError('Free supervisor exited before readiness')
            try:
                if request('/healthz')[0]['status'] == 'ok':
                    return process
            except URLError:
                pass
            time.sleep(.25)
        raise AssertionError('Free topology did not become ready')
    except BaseException:
        stop(process)
        raise

def stop(process):
    process.terminate()
    try:
        assert process.wait(timeout=25) == 0
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        raise

def login():
    body, headers = request('/api/v1/auth/login', {'password':'synthetic-ci-password'})
    assert 'Secure' in headers['Set-Cookie'] and 'HttpOnly' in headers['Set-Cookie']
    return headers['Set-Cookie'].split(';')[0], body['csrf_token']

process = start()
try:
    cookie, csrf = login()
    created, _ = request('/api/v1/jobs', {'kind':'compare_plan','provider':'manual',
        'idempotency_key':uuid.uuid4().hex, 'payload':{'title':'Synthetic test',
        'baseline_minor':150,'alternative_minor':50,'frequency_per_month':20,'setup_cost_minor':0}},cookie,csrf)
    job_id = created['id']
    deadline = time.monotonic()+15
    while time.monotonic() < deadline:
        job, _ = request('/api/v1/jobs/'+job_id,cookie=cookie)
        if job['status'] == 'succeeded':
            assert job['result']['monthly_savings_minor'] == 2000
            break
        time.sleep(.25)
    else:
        raise AssertionError('Separate worker did not complete the job')
finally:
    stop(process)
process = start()
try:
    cookie, csrf = login()
    job, _ = request('/api/v1/jobs/'+job_id,cookie=cookie)
    assert job['status'] == 'succeeded' and job['result']['monthly_savings_minor'] == 2000
    state, _ = request('/api/v1/providers',cookie=cookie)
    assert state['metered_inference_enabled'] is False
finally:
    stop(process)
print('Free topology: migration, secure login, separate worker, durable restart and paid inference off passed')
