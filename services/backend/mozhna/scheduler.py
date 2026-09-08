"""Persistent interval schedules, missed runs coalesce; manual calculations only."""
import time
import uuid
from sqlalchemy import delete, select, update
from .db import connect, LoginSession, Schedule, Job, Record

def tick(factory):
    with factory.begin() as db:
        db.execute(delete(LoginSession).where(LoginSession.expires_at < time.time()))
        now = time.time()
        for schedule in db.scalars(select(Schedule).where(Schedule.next_due <= now).limit(100)).all():
            scheduled_due = schedule.next_due
            changed = db.execute(update(Schedule).where(Schedule.id == schedule.id, Schedule.version == schedule.version)
                                 .values(version=Schedule.version+1, next_due=now+schedule.interval_hours*3600)).rowcount
            if not changed:
                continue
            plan = db.get(Record, schedule.plan_id)
            if not plan or plan.owner_id != schedule.owner_id or plan.data.get('status') != 'active':
                db.delete(schedule)
                continue
            from .schemas import PlanCreate
            payload = {k: plan.data[k] for k in PlanCreate.model_fields}
            db.add(Job(id=uuid.uuid4().hex, owner_id=schedule.owner_id,
                kind='compare_plan', provider='manual', payload=payload,
                idempotency_key=f'schedule:{schedule.id}:{scheduled_due}'))

def main():
    _, factory = connect()
    while True:
        tick(factory)
        time.sleep(30)

if __name__ == '__main__':
    main()
