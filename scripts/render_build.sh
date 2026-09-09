#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pip install uv==0.11.33
python -m uv sync --frozen --no-dev --directory services/backend
npx --yes pnpm@11.19.0 --dir apps/web install --frozen-lockfile
VITE_MOZHNA_FREE_TEST=true npx --yes pnpm@11.19.0 --dir apps/web build
