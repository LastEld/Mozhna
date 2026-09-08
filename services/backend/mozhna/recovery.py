"""Quarantine restored execution state BEFORE restarting any runtime process.

Run only after restoring a backup into the intended DB with API/worker/scheduler
stopped. Financial records are preserved; sessions, schedules and pending jobs
cannot revive stale authorization or repeat a model call automatically.
"""
from sqlalchemy import delete, update
from .db import Job, Schedule, LoginSession, connect, timestamp

def quarantine(factory):
    with factory.begin() as db:
        jobs = db.execute(update(Job).where(Job.status.in_(['queued','running']))
            .values(status='canceled', lease_token=None, lease_until=0,
                    error='RESTORE_QUARANTINED: recreate this job after reviewing restored data.',
                    version=Job.version+1, updated_at=timestamp())).rowcount
        schedules = db.execute(delete(Schedule)).rowcount
        sessions = db.execute(delete(LoginSession)).rowcount
    return {'quarantined_jobs':jobs,'removed_schedules':schedules,'revoked_sessions':sessions}

def main():
    import json
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-stopped', action='store_true', required=True,
                        help='Confirm API, worker and scheduler are stopped')
    parser.parse_args()
    engine, factory = connect()
    try:
        print(json.dumps(quarantine(factory)))
    finally:
        engine.dispose()

if __name__ == '__main__':
    main()
