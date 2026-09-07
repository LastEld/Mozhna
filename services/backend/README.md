# Backend

Предложен FastAPI/Pydantic backend и worker из общего кода. PostgreSQL хранит состояние; API и MCP используют одинаковые application services.

Предлагаемые внутренние модули: money, evidence, plans, actions, connections. Они создаются по мере реализации, не как пустые микросервисы. Money не импортирует сеть/LLM/UI. Выделенный executor нужен позднее для внешних действий.

Runtime, зависимости и миграции ещё не созданы. См. [ADR-0001](../../docs/adr/0001-runtime-shape.md).
