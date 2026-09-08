# Changelog

## 2026-09-07 — Alpha runtime

- Реализованы Money, FastAPI auth/API, SQL jobs/worker/scheduler, Reduce/CSV/export и read-only remote MCP.
- Добавлены React/Vite UI, generated OpenAPI types, Anthropic/Gemini adapters с mock tests.
- Добавлены lockfiles, Alembic, Docker/Compose/Render и Runtime CI.
- Полный cloud deployment, live providers и device QA ещё не выполнены; см. docs/IMPLEMENTATION.md.

## Unreleased

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

Приложение и внешние интеграции пока не реализованы.
