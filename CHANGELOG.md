# Changelog

## Unreleased — устойчивость alpha

- Лимит входа перенесён в БД, добавлены блокировка владельца и повторная проверка сессии перед записью; исправлены гонки удаления и scheduler. Migration `0002_owner_state`.
- Добавлены проверка production schema readiness, лимит размера тела запроса и завершение worker/scheduler по SIGTERM без следующего запуска.
- Добавлены карантин после restore и PostgreSQL dump/restore test в CI.
- Исправлены точность клиентских cents, конфликт открытой формы snapshot, обновление после reconnect и повторная запись при ошибке refresh.
- Добавлены публичная offline-страница, Vitest и Playwright CI для desktop/Android/iPhone эмуляции; runtime verify прошёл (65 backend и 10 frontend tests), браузерный gate ещё выполняется.
- Deployment, облачный restore, настоящие устройства и live provider calls остаются открытыми.

## 2026-09-07 — Alpha runtime

- Реализованы Money, FastAPI auth/API, SQL jobs/worker/scheduler, Reduce/CSV/export и read-only remote MCP.
- Добавлены React/Vite UI, generated OpenAPI types, Anthropic/Gemini adapters с mock tests.
- Добавлены lockfiles, Alembic, Docker/Compose/Render и Runtime CI.
- Полный cloud deployment, live providers и device QA ещё не выполнены; см. docs/IMPLEMENTATION.md.

## 2026-09-07 — Документационный scaffold

### Changed — cloud-first design

- По поручению владельца выбран Python/FastAPI + TypeScript/React/Vite + PostgreSQL.
- Архитектура и roadmap переписаны под API, worker/scheduler, durable cloud jobs и общий PWA-клиент для ПК/Android/iPhone.
- Разделены cloud LLM provider adapters и remote MCP; описаны capabilities, бюджеты, fallback и продолжение плана.
- Добавлены STACK, CLOUD_EXECUTION, LLM_ADAPTERS, CLIENTS, DEPLOYMENT и target infrastructure docs.
- Выбранная архитектура документирована; ресурсы, платные сервисы и runtime не созданы.

### Added

- Восстановленная документация продукта, roadmap, требований и архитектуры.
- Папки клиента, backend, общих компонентов, инфраструктуры, тестов и документов.
- GitHub Issue/PR templates, CODEOWNERS, проверка документации и Dependabot для Actions.
- Синтетические acceptance-примеры и инструкции для разработчиков/AI-агентов.

В момент создания scaffold приложение и внешние интеграции ещё не были реализованы. Текущий статус — в [IMPLEMENTATION](docs/IMPLEMENTATION.md).
