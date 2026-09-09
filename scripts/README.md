# Скрипты

- `python3 scripts/check_docs.py` — обязательные документы, относительные файловые ссылки и синтаксис JSON. Не проверяет внешние сайты и Markdown anchors.
- `uv run python ../../scripts/export_openapi.py` из services/backend — генерация OpenAPI без подключения БД/моделей.
- `python scripts/smoke_http.py` — только для изолированного синтетического CI-контейнера; health, frontend, auth boundary и cookie.

- `scripts/e2e_server.py` — только изолированный Playwright fixture: временная SQLite, синтетический владелец, API и worker; не команда production-запуска.

Runtime tests: [services/backend/tests](../services/backend/tests). Генерация TypeScript: `pnpm generate:api` из apps/web.

Render Free: `bash scripts/render_build.sh` собирает native Python/React service, `bash scripts/render_start.sh` запускает migration и supervisor отдельных процессов. `smoke_free_runtime.py` выполняется только в CI с изолированной TEST_DATABASE_URL и проверяет worker/restart. [Ограничения €0](../docs/DEPLOYMENT.md).
