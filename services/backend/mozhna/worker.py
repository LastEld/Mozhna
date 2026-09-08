import time
from .db import connect
from .jobs import run_once

def main():
    _, factory = connect()
    while True:
        if not run_once(factory):
            time.sleep(2)

if __name__ == '__main__':
    main()
