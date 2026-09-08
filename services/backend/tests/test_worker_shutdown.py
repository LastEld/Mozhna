import os
import signal
import subprocess
import sys

def test_sigterm_finishes_current_job_and_exits_without_another_claim(tmp_path):
    code = '''
from mozhna import worker
import time
def one_job(factory):
    print('CLAIMED', flush=True)
    time.sleep(.25)
    print('COMPLETED', flush=True)
    return True
worker.run_once = one_job
worker.main()
'''
    env = {**os.environ,'DATABASE_URL':'sqlite:///'+str(tmp_path/'shutdown.db')}
    process = subprocess.Popen([sys.executable,'-u','-c',code], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,text=True,env=env)
    try:
        assert process.stdout.readline().strip() == 'CLAIMED'
        process.send_signal(signal.SIGTERM)
        out, err = process.communicate(timeout=5)
        assert process.returncode == 0, err
        assert out.strip() == 'COMPLETED'
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
