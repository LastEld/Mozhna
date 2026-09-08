"""Wait for the release migration before starting a worker on a fresh deployment."""
import time
from sqlalchemy import text
from .db import connect

def main():
    from pathlib import Path
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    required = ScriptDirectory.from_config(Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'))).get_current_head()
    engine, _ = connect()
    for _ in range(60):
        try:
            with engine.connect() as db:
                version = db.scalar(text('SELECT version_num FROM alembic_version'))
                if version == required:
                    return
        except Exception:
            pass
        time.sleep(5)
    raise SystemExit('Database migration is not ready; inspect release task')

if __name__ == '__main__':
    main()
