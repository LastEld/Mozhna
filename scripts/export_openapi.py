"""Run with the backend environment, from any working directory."""
import json
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'services/backend'))
# Schema generation needs no real deployment credentials, DB connection or MCP token.
os.environ['MOZHNA_ENV'] = 'development'
os.environ.pop('MOZHNA_MCP_TOKEN', None)
from mozhna.main import app

(root / 'packages/schemas/openapi.json').write_text(
    json.dumps(app.openapi(), indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
