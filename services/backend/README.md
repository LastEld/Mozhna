# Backend alpha

Python 3.12, FastAPI, SQLAlchemy/Alembic, PostgreSQL для облака, SQLite для разработки. Установка `uv sync --frozen`. Проверки `uv run pytest -q`.

Процессы: `uv run uvicorn mozhna.main:app`, `uv run python -m mozhna.worker`, `uv run python -m mozhna.scheduler`. Перед production запустить `uv run alembic upgrade head`. Полная конфигурация и рабочие папки: [RUNNING](../../docs/RUNNING.md).

Модули: money — чистое ядро; main — cookie auth и API; db — records/sessions/jobs/schedules; jobs/worker/scheduler — долговечные задачи; providers — Anthropic/Gemini; mcp_server — read-only remote tools; imports — CSV. Отдельного action executor нет.

OpenAPI генерируется `uv run python ../../scripts/export_openapi.py`. CLI и CI используют те же сервисы и модели. [Состояние](../../docs/IMPLEMENTATION.md), [финансовая policy](../../docs/MONEY.md).
