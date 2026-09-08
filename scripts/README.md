# Скрипты

- `python3 scripts/check_docs.py` — обязательные документы, относительные файловые ссылки и синтаксис JSON. Не проверяет внешние сайты и Markdown anchors.
- `uv run python ../../scripts/export_openapi.py` из services/backend — генерация OpenAPI без подключения БД/моделей.
- `python scripts/smoke_http.py` — только для изолированного синтетического CI-контейнера; health, frontend, auth boundary и cookie.

Runtime tests: [services/backend/tests](../services/backend/tests). Генерация TypeScript: `pnpm generate:api` из apps/web.
