import os
import signal
import subprocess
import sys
import time

import pytest

from mozhna.free_runtime import child_environment


def wait_for(path):
    deadline = time.monotonic() + 5
    while not path.exists():
        if time.monotonic() > deadline:
            pytest.fail(f'Process never produced {path.name}')
        time.sleep(.02)


def start_supervisor(tmp_path, *, migration=None, crash=False, stubborn=False):
    children = []
    for index in range(3):
        ready = str(tmp_path / f'{index}.ready')
        done = str(tmp_path / f'{index}.done')
        code = f'''
import os, signal, time
from pathlib import Path
def finish(*_):
    Path({done!r}).write_text('stopped')
    raise SystemExit(0)
signal.signal(signal.SIGTERM, {'signal.SIG_IGN' if stubborn and index == 2 else 'finish'})
Path({ready!r}).write_text(str(os.getpid()))
'''
        if crash and index == 0:
            code += "time.sleep(.3)\nraise SystemExit(0)\n"
        else:
            code += "while True: time.sleep(.05)\n"
        children.append([sys.executable, '-c', code])
    code = f'''
import os
from mozhna.free_runtime import supervise
raise SystemExit(supervise(
    {migration or [sys.executable, '-c', 'pass']!r}, {children!r},
    env=os.environ.copy(), shutdown_timeout=.4))
'''
    process = subprocess.Popen([sys.executable, '-c', code], stderr=subprocess.PIPE,
                               text=True)
    return process


def cleanup(process, tmp_path):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    for ready in tmp_path.glob('*.ready'):
        try:
            os.kill(int(ready.read_text()), signal.SIGKILL)
        except ProcessLookupError:
            pass


@pytest.mark.parametrize('sig', [signal.SIGTERM, signal.SIGINT])
def test_shutdown_reaches_all_roles_and_reaps_them(tmp_path, sig):
    process = start_supervisor(tmp_path)
    try:
        for index in range(3):
            wait_for(tmp_path / f'{index}.ready')
        process.send_signal(sig)
        _, error = process.communicate(timeout=3)
        assert process.returncode == 0, error
        assert len(list(tmp_path.glob('*.done'))) == 3
        for ready in tmp_path.glob('*.ready'):
            with pytest.raises(ProcessLookupError):
                os.kill(int(ready.read_text()), 0)
    finally:
        cleanup(process, tmp_path)


def test_even_successful_unexpected_role_exit_stops_peers(tmp_path):
    process = start_supervisor(tmp_path, crash=True)
    try:
        _, error = process.communicate(timeout=5)
        assert process.returncode == 1
        assert 'role exited' in error
        assert (tmp_path / '1.done').exists()
        assert (tmp_path / '2.done').exists()
    finally:
        cleanup(process, tmp_path)


def test_stubborn_child_cannot_hold_shutdown_open(tmp_path):
    process = start_supervisor(tmp_path, stubborn=True)
    try:
        for index in range(3):
            wait_for(tmp_path / f'{index}.ready')
        process.terminate()
        process.communicate(timeout=3)
        assert process.returncode == 0
        assert not (tmp_path / '2.done').exists()
        with pytest.raises(ProcessLookupError):
            os.kill(int((tmp_path / '2.ready').read_text()), 0)
    finally:
        cleanup(process, tmp_path)


def test_migration_failure_never_starts_roles(tmp_path):
    process = start_supervisor(tmp_path, migration=[sys.executable, '-c', 'raise SystemExit(7)'])
    try:
        _, error = process.communicate(timeout=5)
        assert process.returncode == 1
        assert 'migration failed' in error
        assert not list(tmp_path.glob('*.ready'))
    finally:
        cleanup(process, tmp_path)


def test_shutdown_during_migration_never_starts_roles(tmp_path):
    marker = tmp_path / 'migration.pid'
    code = f'from pathlib import Path; import os, time; Path({str(marker)!r}).write_text(str(os.getpid())); time.sleep(30)'
    process = start_supervisor(tmp_path, migration=[sys.executable, '-c', code])
    try:
        wait_for(marker)
        process.terminate()
        process.communicate(timeout=3)
        assert process.returncode == 0
        assert not list(tmp_path.glob('*.ready'))
        with pytest.raises(ProcessLookupError):
            os.kill(int(marker.read_text()), 0)
    finally:
        cleanup(process, tmp_path)


def test_free_environment_requires_postgres_and_disables_paid_inference():
    with pytest.raises(ValueError, match='PostgreSQL'):
        child_environment({'DATABASE_URL': 'sqlite:///temporary.db'})
    with pytest.raises(ValueError, match='paid inference'):
        child_environment({'MOZHNA_ALLOW_PAID_INFERENCE': 'true'})
    env = child_environment({'DATABASE_URL': 'postgresql://synthetic/db'})
    assert env['MOZHNA_ENV'] == 'production'
    assert env['MOZHNA_ALLOW_PAID_INFERENCE'] == 'false'
    assert child_environment({'MOZHNA_ENV': 'development'})['MOZHNA_ALLOW_PAID_INFERENCE'] == 'false'
