# Проверки

Runtime tests находятся в [services/backend/tests](../services/backend/tests): Money, API/ownership/versions, imports, jobs, schedules, provider contracts и настоящий MCP HTTP client. PostgreSQL concurrency test использует отдельную disposable DB в CI.

Команды и границы: [RUNNING](../docs/RUNNING.md), [IMPLEMENTATION](../docs/IMPLEMENTATION.md). Fixtures содержат только синтетические значения. Полевые проверки полезности и реальные устройства не тестировались.
