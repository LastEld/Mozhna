# Облачный backend

Выбраны Python + FastAPI + Pydantic + SQLAlchemy + Alembic + PostgreSQL. Один image запускает разные процессы api, worker и scheduler. Runtime, entrypoints и uv.lock появятся вместе с первым кодом.

Внутренние модули: money, evidence, plans, actions, connections, model_providers, jobs. Money живёт в domain, не импортирует сеть/LLM/UI. API и remote MCP используют одинаковые application services и policy.

JobStore/PostgreSQL обеспечивает долговечное исполнение; ModelProvider изолирует API разных LLM. Изолированный executor добавляется для внешних действий и хранит минимум разрешённых sessions.

Контракты: [ARCHITECTURE](../../docs/ARCHITECTURE.md), [CLOUD_EXECUTION](../../docs/CLOUD_EXECUTION.md), [LLM_ADAPTERS](../../docs/LLM_ADAPTERS.md).
