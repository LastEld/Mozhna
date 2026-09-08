"""Durable, leased, cancel-safe jobs. Only read-only/draft operations are permitted."""
import time
import uuid
from sqlalchemy import select, update, or_, and_
from .db import Job, timestamp

LEASE_SECONDS = 120
MAX_ATTEMPTS = 3


def job_dict(job):
    return {name: getattr(job, name) for name in ('id','kind','provider','status','payload','result','error','attempts','version','created_at','updated_at')}


def claim(factory):
    now = time.time()
    with factory.begin() as db:
        candidates = db.scalars(select(Job).where(or_(Job.status == 'queued', and_(Job.status == 'running', Job.lease_until < now))).order_by(Job.created_at).limit(20)).all()
        for job in candidates:
            if job.attempts >= MAX_ATTEMPTS:
                db.execute(update(Job).where(Job.id == job.id, Job.version == job.version).values(status='failed',error='Worker retry limit exceeded; start a new job.',version=job.version+1,updated_at=timestamp()))
                continue
            token = uuid.uuid4().hex
            changed = db.execute(update(Job).where(Job.id == job.id, Job.version == job.version).values(status='running',lease_token=token,lease_until=now+LEASE_SECONDS,attempts=job.attempts+1,version=job.version+1,updated_at=timestamp())).rowcount
            if changed:
                return job.id, token
    return None


def execute(job):
    from .providers import execute_job, ProviderError
    if job.kind == 'compare_plan' and job.provider == 'manual':
        from .schemas import PlanCreate
        payload = PlanCreate.model_validate(job.payload)
        gross = (payload.baseline_minor-payload.alternative_minor)*payload.frequency_per_month
        from .money import SAFE_INTEGER
        if abs(gross) > SAFE_INTEGER or abs(gross-payload.setup_cost_minor) > SAFE_INTEGER:
            raise ProviderError('unsafe_scenario_amount')
        return {'mode':'scenario','monthly_savings_minor':gross,'first_month_savings_minor':gross-payload.setup_cost_minor,'currency':payload.currency,'explanation':'Arithmetic scenario from your inputs; savings are not observed income.'}
    try:
        return execute_job(job.kind, job.payload, job.provider)
    except ProviderError:
        raise


def run_once(factory):
    claimed = claim(factory)
    if not claimed:
        return False
    job_id, token = claimed
    with factory() as db:
        job = db.get(Job, job_id)
        if not job or job.status != 'running' or job.lease_token != token:
            return True
        try:
            result = execute(job)
            values = {'status':'succeeded','result':result,'error':None}
        except Exception as exc:
            # Do not persist provider response bodies, credentials, or request payloads in errors.
            code = getattr(exc, 'code', type(exc).__name__)
            values = {'status':'failed','error':f'Job could not complete ({code}). Check inputs and provider configuration.'}
    with factory.begin() as db:
        db.execute(update(Job).where(Job.id == job_id,Job.status == 'running',Job.lease_token == token).values(**values,lease_until=0,lease_token=None,version=Job.version+1,updated_at=timestamp()))
    return True
