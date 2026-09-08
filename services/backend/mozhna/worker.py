import signal
from threading import Event
from .db import connect
from .jobs import run_once

def main():
    engine, factory = connect()
    stop = Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    try:
        while not stop.is_set():
            if not run_once(factory):
                stop.wait(2)
    finally:
        # A running job completes before shutdown; no new lease is claimed.
        engine.dispose()

if __name__ == '__main__':
    main()
