"""Container entry point for long-lived processes after the release migration."""
import argparse
from .wait_db import main as wait_db

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('role', choices=['worker', 'scheduler'])
    args = parser.parse_args()
    wait_db()
    if args.role == 'worker':
        from .worker import main as run
    else:
        from .scheduler import main as run
    run()

if __name__ == '__main__':
    main()
