"""Persistent interval schedules, missed runs coalesce; manual calculations only."""
import time
import uuid
import signal
from threading import Event
from sqlalchemy import delete, select, update
from .db import connect, LoginSession, Schedule, Job, Record, lock_owner

def tick(factory):
    now = time.time()
    # Cleanup has its own transaction: do not hold session locks while acquiring
    # an owner lock (API writers acquire owner first, then session rows).
    with factory.begin() as db:
        db.execute(delete(LoginSession).where(LoginSession.expires_at < now))
    # Selection is advisory. Re-read each candidate after owner serialization;
    # erase, cancellation, or another scheduler may have changed it meanwhile.
    with factory() as db:
        candidates = db.execute(select(Schedule.id, Schedule.owner_id)
            .where(Schedule.next_due <= now).order_by(Schedule.next_due).limit(100)).all()
    for schedule_id, owner_id in candidates:
        with factory.begin() as db:
            lock_owner(db, owner_id)
            schedule = db.get(Schedule, schedule_id)
            if not schedule or schedule.owner_id != owner_id or schedule.next_due > now:
                continue
            plan = db.get(Record, schedule.plan_id)
            if not plan or plan.owner_id != owner_id or plan.data.get('status') != 'active':
                db.delete(schedule)
                continue
            scheduled_due = schedule.next_due
            changed = db.execute(update(Schedule).where(Schedule.id == schedule.id,
                    Schedule.owner_id == owner_id, Schedule.version == schedule.version)
                .values(version=Schedule.version+1, next_due=now+schedule.interval_hours*3600)).rowcount
            if not changed:
                continue
            from .schemas import PlanCreate
            payload = {k: plan.data[k] for k in PlanCreate.model_fields}
            db.add(Job(id=uuid.uuid4().hex, owner_id=owner_id,
                kind='compare_plan', provider='manual', payload=payload,
                idempotency_key=f'schedule:{schedule.id}:{scheduled_due}'))

def main():
    engine, factory = connect()
    stop = Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    try:
        while not stop.is_set():
            tick(factory)
            stop.wait(30)
    finally:
        engine.dispose()

if __name__ == '__main__':
    main()
