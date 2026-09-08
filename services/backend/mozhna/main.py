"""MOZHNA single-owner alpha. Cloud API with persistent jobs and explicit limits."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid

from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, update, delete, func
from sqlalchemy.exc import IntegrityError

from .db import Base, Record, LoginSession, Job, Schedule, connect, timestamp
from .money import MoneySnapshot, evaluate
from .schemas import (Login, SnapshotUpdate, Simulation, PlanCreate, PlanChange,
                      Observation, TransactionCreate, ImportRequest, JobCreate, Erase)
from .schemas import Calculation, SnapshotView, AuthView, PlanView, TransactionView, JobView, Page, ScheduleCreate, ScheduleView, ProviderStateView
from .jobs import job_dict
from .imports import parse_csv
from .providers import provider_status


def create_app(database_url=None):
    engine, factory = connect(database_url)
    production = os.getenv('MOZHNA_ENV', 'development') == 'production'
    password = os.getenv('MOZHNA_PASSWORD', '')
    owner = os.getenv('MOZHNA_OWNER_ID', 'owner')
    origin = os.getenv('PUBLIC_ORIGIN', os.getenv('RENDER_EXTERNAL_URL', '')).rstrip('/')
    mcp_token = os.getenv('MOZHNA_MCP_TOKEN', '')
    if mcp_token and len(mcp_token) < 32:
        raise RuntimeError('MOZHNA_MCP_TOKEN must contain at least 32 characters')
    mcp_app = None
    if mcp_token:
        from .mcp_server import build_mcp
        from mcp.server.transport_security import TransportSecuritySettings
        from urllib.parse import urlparse
        hosts = ['127.0.0.1:*', 'localhost:*', 'testserver']
        if origin:
            hosts.append(urlparse(origin).netloc)
        mcp_app = build_mcp(factory, owner).streamable_http_app(
            streamable_http_path='/', json_response=True, stateless_http=True,
            transport_security=TransportSecuritySettings(allowed_hosts=hosts,
                allowed_origins=[origin] if origin else ['http://127.0.0.1:*','http://localhost:*']))
    if production and (len(password) < 16 or not origin.startswith('https://')):
        raise RuntimeError('Production requires MOZHNA_PASSWORD >=16 characters and HTTPS PUBLIC_ORIGIN')

    @asynccontextmanager
    async def lifespan(app):
        if not production:
            Base.metadata.create_all(engine)
        if mcp_app:
            async with mcp_app.router.lifespan_context(mcp_app):
                yield
        else:
            yield
        engine.dispose()

    app = FastAPI(title='MOZHNA API', version='0.1.0', lifespan=lifespan,
                  docs_url=None if production else '/docs', redoc_url=None)
    app.state.factory = factory
    app.state.engine = engine
    attempts = {}

    @app.middleware('http')
    async def boundaries(request, call_next):
        if request.url.path == '/mcp' or request.url.path.startswith('/mcp/'):
            if not mcp_app:
                return JSONResponse({'detail':'MCP is not enabled'}, status_code=404)
            authorization = request.headers.get('authorization', '')
            if not hmac.compare_digest(authorization.encode(), ('Bearer '+mcp_token).encode()):
                return JSONResponse({'detail':'Bearer token required'}, status_code=401,
                                    headers={'WWW-Authenticate':'Bearer','Cache-Control':'no-store'})
        if request.url.path.startswith('/api/'):
            try:
                if int(request.headers.get('content-length', '0')) > 2_500_000:
                    return JSONResponse({'detail': 'Request too large'}, status_code=413)
            except ValueError:
                return JSONResponse({'detail': 'Invalid content length'}, status_code=400)
            supplied = request.headers.get('origin')
            allowed = origin or str(request.base_url).rstrip('/')
            if request.method not in ('GET', 'HEAD', 'OPTIONS') and supplied and supplied != allowed:
                return JSONResponse({'detail': 'Origin not allowed'}, status_code=403)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if request.url.path.startswith(('/api/','/mcp')):
            response.headers['Cache-Control'] = 'no-store'
        return response

    def authenticate(request: Request):
        token = request.cookies.get('mozhna_session')
        if not token:
            raise HTTPException(401, 'Sign in required')
        digest = hashlib.sha256(token.encode()).hexdigest()
        with factory() as db:
            session = db.get(LoginSession, digest)
            if not session or session.expires_at < time.time():
                raise HTTPException(401, 'Session expired')
            if request.method not in ('GET', 'HEAD') and not hmac.compare_digest(request.headers.get('x-csrf-token', ''), session.csrf):
                raise HTTPException(403, 'CSRF token required')
            return {'owner_id': session.owner_id, 'csrf_token': session.csrf, 'token_hash': digest}

    def record(db, record_id, kind, auth):
        item = db.get(Record, record_id)
        if not item or item.owner_id != auth['owner_id'] or item.kind != kind:
            raise HTTPException(404, 'Not found')
        return item

    def view(item):
        result = {**item.data, 'id': item.id, 'version': item.version, 'created_at': item.created_at}
        if item.kind == 'plan':
            spent = sum(o['amount_minor'] for o in item.data['observations'])
            result.update(observed_spend_minor=spent, observed_difference_minor=(
                item.data['baseline_minor']*len(item.data['observations'])-spent-item.data['setup_cost_minor']))
        return result

    def snapshot_view(db, auth):
        item = db.get(Record, 'snapshot:'+auth['owner_id'])
        if not item:
            return {'version': 0, 'snapshot': None, 'calculation': None}
        return {'version': item.version, 'snapshot': item.data,
                'calculation': evaluate(item.data)}

    @app.get('/healthz')
    def health():
        from sqlalchemy import text
        with engine.connect() as db:
            db.execute(text('SELECT 1'))
        return {'status': 'ok', 'version': '0.1.0'}

    @app.post('/api/v1/auth/login', response_model=AuthView)
    def login(body: Login, request: Request, response: Response):
        if not password:
            raise HTTPException(503, 'Owner password is not configured')
        address = request.client.host if request.client else 'unknown'
        now = time.time()
        recent = [t for t in attempts.get(address, []) if t > now-300]
        if len(recent) >= 8:
            raise HTTPException(429, 'Try again in five minutes')
        if len(attempts) > 10000:
            attempts.clear()
        attempts[address] = recent+[now]
        if not hmac.compare_digest(hashlib.sha256(body.password.encode()).digest(), hashlib.sha256(password.encode()).digest()):
            raise HTTPException(401, 'Incorrect password')
        attempts.pop(address, None)
        token, csrf = secrets.token_urlsafe(40), secrets.token_urlsafe(32)
        with factory.begin() as db:
            db.add(LoginSession(token_hash=hashlib.sha256(token.encode()).hexdigest(),
                                csrf=csrf, owner_id=owner, expires_at=now+43200))
        response.set_cookie('mozhna_session', token, httponly=True, secure=production,
                            samesite='strict', max_age=43200, path='/')
        return {'user': {'id': owner, 'name': 'Мій простір'}, 'csrf_token': csrf}

    @app.get('/api/v1/auth/me', response_model=AuthView)
    def me(auth=Depends(authenticate)):
        return {'user': {'id': auth['owner_id'], 'name': 'Мій простір'}, 'csrf_token': auth['csrf_token']}

    @app.post('/api/v1/auth/logout')
    def logout(response: Response, auth=Depends(authenticate)):
        with factory.begin() as db:
            db.execute(delete(LoginSession).where(LoginSession.token_hash == auth['token_hash']))
        response.delete_cookie('mozhna_session', path='/')
        return {'ok': True}

    @app.get('/api/v1/snapshot', response_model=SnapshotView)
    def get_snapshot(auth=Depends(authenticate)):
        with factory() as db:
            return snapshot_view(db, auth)

    @app.put('/api/v1/snapshot', response_model=SnapshotView)
    def set_snapshot(body: SnapshotUpdate, auth=Depends(authenticate)):
        key = 'snapshot:'+auth['owner_id']
        with factory.begin() as db:
            item = db.get(Record, key)
            if item:
                changed = db.execute(update(Record).where(Record.id == key, Record.owner_id == auth['owner_id'], Record.version == body.expected_version)
                    .values(data=body.snapshot.model_dump(mode='json'), version=Record.version+1)).rowcount
                if not changed:
                    raise HTTPException(409, 'State changed on another device. Reload first.')
                db.expire_all()
            else:
                if body.expected_version != 0:
                    raise HTTPException(409, 'State version mismatch')
                db.add(Record(id=key, owner_id=auth['owner_id'], kind='snapshot', version=1, data=body.snapshot.model_dump(mode='json')))
                try:
                    db.flush()
                except IntegrityError:
                    raise HTTPException(409, 'State changed. Reload first.') from None
            return snapshot_view(db, auth)

    @app.post('/api/v1/simulate', response_model=Calculation)
    def simulate(body: Simulation, auth=Depends(authenticate)):
        with factory() as db:
            item = db.get(Record, 'snapshot:'+auth['owner_id'])
            return evaluate(item.data if item else MoneySnapshot(), body.amount_minor)

    @app.get('/api/v1/plans', response_model=Page[PlanView])
    def plans(auth=Depends(authenticate)):
        with factory() as db:
            return {'items': [view(p) for p in db.scalars(select(Record).where(Record.owner_id == auth['owner_id'], Record.kind == 'plan').order_by(Record.created_at.desc()))]}

    @app.post('/api/v1/plans', status_code=201, response_model=PlanView)
    def add_plan(body: PlanCreate, auth=Depends(authenticate)):
        data = body.model_dump()
        potential = (body.baseline_minor-body.alternative_minor)*body.frequency_per_month
        if abs(potential) > 2**53-1 or abs(potential-body.setup_cost_minor)>2**53-1:
            raise HTTPException(422, 'Arithmetic outside supported range')
        data.update(status='proposed', observations=[], scenario_savings_minor=potential,
                    first_month_savings_minor=potential-body.setup_cost_minor)
        item = Record(id=uuid.uuid4().hex, owner_id=auth['owner_id'], kind='plan', data=data)
        with factory.begin() as db:
            db.add(item)
            db.flush()
            return view(item)

    @app.patch('/api/v1/plans/{plan_id}', response_model=PlanView)
    def change_plan(plan_id: str, body: PlanChange, auth=Depends(authenticate)):
        with factory.begin() as db:
            item = record(db, plan_id, 'plan', auth)
            data = {**item.data, 'status': body.status, 'rejection_reason': body.rejection_reason}
            count = db.execute(update(Record).where(Record.id == plan_id, Record.version == body.expected_version)
                               .values(data=data, version=Record.version+1)).rowcount
            if not count:
                raise HTTPException(409, 'Plan changed. Reload first.')
            db.expire_all()
            return view(db.get(Record, plan_id))

    @app.post('/api/v1/plans/{plan_id}/observations', response_model=PlanView)
    def add_observation(plan_id: str, body: Observation, auth=Depends(authenticate)):
        with factory.begin() as db:
            item = record(db, plan_id, 'plan', auth)
            if item.data['status'] != 'active':
                raise HTTPException(409, 'Activate the plan before recording results')
            observations = item.data.get('observations', [])
            if len(observations) >= 1000:
                raise HTTPException(422, 'Observation limit reached')
            data = {**item.data, 'observations': observations+[body.model_dump(mode='json')]}
            spent = sum(o['amount_minor'] for o in data['observations'])
            baseline = data['baseline_minor']*len(data['observations'])
            if any(abs(n) > 2**53-1 for n in (spent, baseline, baseline-spent-data['setup_cost_minor'])):
                raise HTTPException(422, 'Observed arithmetic outside supported range')
            if not db.execute(update(Record).where(Record.id == plan_id, Record.version == item.version)
                              .values(data=data, version=Record.version+1)).rowcount:
                raise HTTPException(409, 'Plan changed. Reload first.')
            db.expire_all()
            return view(db.get(Record, plan_id))

    @app.get('/api/v1/transactions', response_model=Page[TransactionView])
    def transactions(auth=Depends(authenticate)):
        with factory() as db:
            return {'items': [view(t) for t in db.scalars(select(Record).where(Record.owner_id == auth['owner_id'], Record.kind == 'transaction').order_by(Record.created_at.desc()).limit(1000))]}

    @app.post('/api/v1/transactions', status_code=201, response_model=TransactionView)
    def add_transaction(body: TransactionCreate, auth=Depends(authenticate)):
        item = Record(id=uuid.uuid4().hex, owner_id=auth['owner_id'], kind='transaction', data=body.model_dump(mode='json'))
        with factory.begin() as db:
            db.add(item)
            db.flush()
            return view(item)

    @app.post('/api/v1/transactions/import')
    def import_transactions(body: ImportRequest, auth=Depends(authenticate)):
        try:
            rows = parse_csv(body.csv_text, body.currency)
        except ValueError as exc:
            raise HTTPException(422, str(exc)[:400]) from None
        added = skipped = 0
        with factory.begin() as db:
            for data in rows:
                key = hashlib.sha256((auth['owner_id']+':csv:'+data.pop('source_key')).encode()).hexdigest()
                if db.get(Record, key):
                    skipped += 1
                    continue
                try:
                    with db.begin_nested():
                        db.add(Record(id=key, owner_id=auth['owner_id'], kind='transaction', data=data))
                        db.flush()
                    added += 1
                except IntegrityError:
                    skipped += 1
        return {'added': added, 'skipped': skipped, 'snapshot_changed': False}

    @app.get('/api/v1/jobs', response_model=Page[JobView])
    def jobs(auth=Depends(authenticate)):
        with factory() as db:
            return {'items': [job_dict(j) for j in db.scalars(select(Job).where(Job.owner_id == auth['owner_id']).order_by(Job.created_at.desc()).limit(100))]}

    @app.post('/api/v1/jobs', status_code=202, response_model=JobView)
    def add_job(body: JobCreate, auth=Depends(authenticate)):
        if len(json.dumps(body.payload)) > 20000:
            raise HTTPException(422, 'Task context too large')
        if body.kind == 'compare_plan':
            try:
                PlanCreate.model_validate(body.payload)
            except ValueError:
                raise HTTPException(422, 'Invalid plan context') from None
        elif body.kind == 'draft_application' and not all(body.payload.get(k) for k in ('profile_facts','job_description')):
            raise HTTPException(422, 'Profile facts and job description required')
        elif body.kind == 'income_search' and not body.payload.get('role'):
            raise HTTPException(422, 'Role required')
        with factory.begin() as db:
            old = db.scalar(select(Job).where(Job.owner_id == auth['owner_id'], Job.idempotency_key == body.idempotency_key))
            if old:
                if (old.payload, old.kind, old.provider) != (body.payload, body.kind, body.provider):
                    raise HTTPException(409, 'Idempotency key already used for another command')
                return job_dict(old)
            # Owner row lock serializes quota allocation for PostgreSQL.
            db.scalars(select(LoginSession).where(LoginSession.owner_id == auth['owner_id']).with_for_update()).all()
            cutoff = datetime.fromtimestamp(time.time()-86400, timezone.utc).isoformat()
            count = db.scalar(select(func.count()).select_from(Job).where(Job.owner_id == auth['owner_id'], Job.created_at >= cutoff))
            if count >= int(os.getenv('MOZHNA_DAILY_JOB_LIMIT','40')):
                raise HTTPException(429, 'Daily job limit reached')
            if body.provider != 'manual':
                provider = next(p for p in provider_status() if p['id'] == body.provider)
                if not provider['available'] or os.getenv('MOZHNA_ALLOW_PAID_INFERENCE','false') != 'true':
                    raise HTTPException(409, 'Cloud model is not configured or metered inference is disabled')
            elif body.kind == 'draft_application':
                raise HTTPException(409, 'Drafting requires a configured model')
            item = Job(id=uuid.uuid4().hex, owner_id=auth['owner_id'], kind=body.kind,
                       provider=body.provider, payload=body.payload, idempotency_key=body.idempotency_key)
            db.add(item)
            try:
                db.flush()
            except IntegrityError:
                raise HTTPException(409, 'Command already queued; reload task list') from None
            return job_dict(item)

    @app.get('/api/v1/jobs/{job_id}', response_model=JobView)
    def get_job(job_id: str, auth=Depends(authenticate)):
        with factory() as db:
            item = db.get(Job, job_id)
            if not item or item.owner_id != auth['owner_id']:
                raise HTTPException(404, 'Not found')
            return job_dict(item)

    @app.post('/api/v1/jobs/{job_id}/cancel', response_model=JobView)
    def cancel_job(job_id: str, auth=Depends(authenticate)):
        with factory.begin() as db:
            item = db.get(Job, job_id)
            if not item or item.owner_id != auth['owner_id']:
                raise HTTPException(404, 'Not found')
            db.execute(update(Job).where(Job.id == job_id, Job.status.in_(['queued','running']))
                .values(status='canceled', lease_token=None, lease_until=0, version=Job.version+1, updated_at=timestamp()))
            db.expire_all()
            return job_dict(db.get(Job, job_id))

    @app.get('/api/v1/providers', response_model=ProviderStateView)
    def providers(auth=Depends(authenticate)):
        return {'items': provider_status(), 'metered_inference_enabled': os.getenv('MOZHNA_ALLOW_PAID_INFERENCE','false') == 'true',
                'limitations': ['Bank sync not connected', 'Live job search not connected', 'External submissions disabled', 'MCP OAuth pending'],
                'daily_job_limit': int(os.getenv('MOZHNA_DAILY_JOB_LIMIT','40'))}

    @app.get('/api/v1/schedules', response_model=Page[ScheduleView])
    def schedules(auth=Depends(authenticate)):
        with factory() as db:
            return {'items': [{'id':s.id, 'plan_id':s.plan_id, 'interval_hours':s.interval_hours, 'next_due':s.next_due}
                              for s in db.scalars(select(Schedule).where(Schedule.owner_id == auth['owner_id']))]}

    @app.post('/api/v1/schedules', status_code=201, response_model=ScheduleView)
    def add_schedule(body: ScheduleCreate, auth=Depends(authenticate)):
        with factory.begin() as db:
            db.scalars(select(LoginSession).where(LoginSession.owner_id == auth['owner_id']).with_for_update()).all()
            plan = record(db, body.plan_id, 'plan', auth)
            if plan.data['status'] != 'active':
                raise HTTPException(409, 'Only active plans can be scheduled')
            existing = db.scalar(select(Schedule).where(Schedule.owner_id == auth['owner_id'], Schedule.plan_id == plan.id))
            if existing:
                return {'id':existing.id, 'next_due':existing.next_due, 'plan_id':existing.plan_id, 'interval_hours':existing.interval_hours}
            count = db.scalar(select(func.count()).select_from(Schedule).where(Schedule.owner_id == auth['owner_id']))
            if count >= 10:
                raise HTTPException(422, 'Maximum 10 active schedules')
            s = Schedule(id=uuid.uuid4().hex, owner_id=auth['owner_id'], plan_id=plan.id,
                         interval_hours=body.interval_hours, next_due=time.time()+body.interval_hours*3600)
            db.add(s)
            try:
                db.flush()
            except IntegrityError:
                raise HTTPException(409, 'Schedule already exists; reload schedules') from None
            return {'id':s.id, 'next_due':s.next_due, 'plan_id':s.plan_id, 'interval_hours':s.interval_hours}

    @app.delete('/api/v1/schedules/{schedule_id}')
    def remove_schedule(schedule_id: str, auth=Depends(authenticate)):
        with factory.begin() as db:
            db.execute(delete(Schedule).where(Schedule.id == schedule_id, Schedule.owner_id == auth['owner_id']))
        return {'deleted':True}

    @app.get('/api/v1/export')
    def export(auth=Depends(authenticate)):
        with factory() as db:
            return {'format_version': 1, 'exported_at': timestamp(),
                    'records': [{**view(r), 'kind': r.kind} for r in db.scalars(select(Record).where(Record.owner_id == auth['owner_id']))],
                    'jobs': [job_dict(j) for j in db.scalars(select(Job).where(Job.owner_id == auth['owner_id']))],
                    'schedules': [{'id':s.id,'plan_id':s.plan_id,'interval_hours':s.interval_hours,'next_due':s.next_due}
                                  for s in db.scalars(select(Schedule).where(Schedule.owner_id == auth['owner_id']))]}

    @app.delete('/api/v1/data')
    def erase(body: Erase, response: Response, auth=Depends(authenticate)):
        with factory.begin() as db:
            db.execute(delete(Schedule).where(Schedule.owner_id == auth['owner_id']))
            db.execute(delete(Job).where(Job.owner_id == auth['owner_id']))
            db.execute(delete(Record).where(Record.owner_id == auth['owner_id']))
            db.execute(delete(LoginSession).where(LoginSession.owner_id == auth['owner_id']))
        response.delete_cookie('mozhna_session', path='/')
        return {'deleted': True, 'external_dispatched_requests_cannot_be_recalled': True}

    if mcp_app:
        app.mount('/mcp', mcp_app)

    web = Path(os.getenv('WEB_DIST_DIR', str(Path(__file__).resolve().parents[3]/'apps/web/dist'))).resolve()
    if web.is_dir():
        if (web/'assets').is_dir():
            app.mount('/assets', StaticFiles(directory=web/'assets'), name='assets')

        @app.get('/{path:path}', include_in_schema=False)
        def frontend(path: str):
            if path.startswith(('api/', 'mcp')):
                raise HTTPException(404, 'Not implemented')
            candidate = (web/path).resolve()
            if candidate.is_relative_to(web) and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(web/'index.html')
    return app


app = create_app()
