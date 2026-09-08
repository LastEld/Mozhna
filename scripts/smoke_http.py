"""Smoke test an isolated synthetic CI container; never run against user data."""
import json
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

base = 'http://127.0.0.1:8000'
for _ in range(30):
    try:
        with urlopen(base+'/healthz', timeout=2) as response:
            assert json.load(response)['status'] == 'ok'
        break
    except URLError:
        time.sleep(1)
else:
    raise SystemExit('Container health check did not become ready')
with urlopen(base) as response:
    assert '<div id="root">' in response.read().decode()
try:
    urlopen(base+'/api/v1/snapshot')
    raise AssertionError('Snapshot was exposed without authentication')
except HTTPError as exc:
    assert exc.code == 401
request = Request(base+'/api/v1/auth/login', data=json.dumps({'password':'synthetic-ci-password'}).encode(),
                  headers={'Content-Type':'application/json'}, method='POST')
with urlopen(request) as response:
    cookie = response.headers.get('Set-Cookie', '')
    assert 'Secure' in cookie and 'HttpOnly' in cookie
    assert json.load(response)['csrf_token']
print('Container serves frontend, healthy database, protected API and secure login cookie')
