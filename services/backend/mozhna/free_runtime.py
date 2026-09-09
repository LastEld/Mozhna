"""Render free testing: API, worker and scheduler share one web instance.

All three processes pause when Render spins the web service down. This is not
an always-on scheduler; durable jobs resume after a real request wakes the app.
No keep-alive traffic or paid inference is enabled by this launcher.
"""
import os
from pathlib import Path
import signal
import subprocess
import sys
from threading import Event
import time

from sqlalchemy.engine import make_url


def child_environment(source):
    env = dict(source)
    if env.get('MOZHNA_ALLOW_PAID_INFERENCE', 'false').strip().lower() not in (
        '', 'false', '0', 'no', 'off',
    ):
        raise ValueError('Free runtime refuses paid inference')
    env['MOZHNA_ALLOW_PAID_INFERENCE'] = 'false'
    env.setdefault('MOZHNA_ENV', 'production')
    if env['MOZHNA_ENV'] == 'production':
        try:
            postgres = make_url(env.get('DATABASE_URL', '')).get_backend_name() == 'postgresql'
        except Exception:
            postgres = False
        if not postgres:
            raise ValueError('Free production runtime requires an external PostgreSQL database')
    return env


def _stop(children, timeout):
    # A shared deadline bounds the entire shutdown, rather than each process.
    for child in children:
        if child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    deadline = time.monotonic() + timeout
    for child in children:
        try:
            child.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait()


def supervise(migration, commands, *, env, cwd=None, shutdown_timeout=20,
              migration_timeout=120):
    """Migrate before launch; stop the whole instance if any role exits.

    Commands are injectable for subprocess lifecycle tests. Call from the main
    thread because Render's SIGTERM must be forwarded even during migrations.
    """
    stop = Event()
    children = []
    handlers = {}
    for sig in (signal.SIGTERM, signal.SIGINT):
        handlers[sig] = signal.signal(sig, lambda *_: stop.set())
    try:
        def launch(command):
            child = subprocess.Popen(command, env=env, cwd=cwd, start_new_session=True)
            children.append(child)
            return child

        migrating = launch(migration)
        deadline = time.monotonic() + migration_timeout
        while migrating.poll() is None:
            if stop.wait(.1):
                return 0
            if time.monotonic() >= deadline:
                print('Database migration timed out; runtime was not started', file=sys.stderr)
                return 1
        if migrating.returncode:
            print('Database migration failed; runtime was not started', file=sys.stderr)
            return 1
        children.clear()
        for command in commands:
            if stop.is_set():
                return 0
            launch(command)
        while not stop.wait(.1):
            if any(child.poll() is not None for child in children):
                print('A runtime role exited; stopping the instance', file=sys.stderr)
                return 1
        return 0
    finally:
        _stop(children, shutdown_timeout)
        for sig, handler in handlers.items():
            signal.signal(sig, handler)


def main():
    env = child_environment(os.environ)
    port = int(env.get('PORT', '10000'))
    if not 1 <= port <= 65535:
        raise ValueError('PORT must be between 1 and 65535')
    python = sys.executable
    return supervise(
        [python, '-m', 'alembic', 'upgrade', 'head'],
        [
            [python, '-m', 'uvicorn', 'mozhna.main:app', '--host', '0.0.0.0', '--port', str(port)],
            [python, '-m', 'mozhna.worker'],
            [python, '-m', 'mozhna.scheduler'],
        ],
        env=env,
        cwd=Path(__file__).resolve().parents[1],
    )


if __name__ == '__main__':
    raise SystemExit(main())
