"""Isolated, synthetic UI test stack. Not a production entrypoint."""
import os
from pathlib import Path
import signal
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Event

root = Path(__file__).resolve().parents[1]
backend = root / 'services/backend'
stop = Event()
for sig in (signal.SIGTERM, signal.SIGINT):
    signal.signal(sig, lambda *_: stop.set())
with TemporaryDirectory(prefix='mozhna-e2e-') as temporary:
    env = {**os.environ, 'MOZHNA_ENV':'development',
           'DATABASE_URL':'sqlite:///'+str(Path(temporary)/'test.db'),
           'MOZHNA_PASSWORD':'synthetic-e2e-password', 'MOZHNA_OWNER_ID':'e2e-owner',
           'MOZHNA_MCP_TOKEN':'', 'MOZHNA_ALLOW_PAID_INFERENCE':'false',
           'PUBLIC_ORIGIN':'http://127.0.0.1:8765', 'WEB_DIST_DIR':str(root/'apps/web/dist')}
    subprocess.run([sys.executable,'-m','alembic','upgrade','head'], cwd=backend, env=env, check=True)
    children = [subprocess.Popen([sys.executable,'-m',*command], cwd=backend, env=env)
                for command in (['uvicorn','mozhna.main:app','--host','127.0.0.1','--port','8765'],
                                ['mozhna.worker'])]
    try:
        while not stop.wait(.5):
            if any(child.poll() is not None for child in children):
                raise SystemExit('Synthetic API/worker stopped unexpectedly')
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
