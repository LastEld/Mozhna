#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../services/backend"
export WEB_DIST_DIR="$(cd ../../apps/web/dist && pwd)"
exec .venv/bin/python -m mozhna.free_runtime
