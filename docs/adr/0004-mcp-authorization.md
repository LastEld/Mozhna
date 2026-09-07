# Remote MCP и authorization

Статус: DECIDED. Дата: 2026-09-07. Выбор по поручению владельца о cloud/model-neutral работе; [CONTEXT](../CONTEXT.md).

## Решение

HTTPS Streamable HTTP remote MCP над общими application services; resource-scoped OAuth tokens, owner/scopes и серверная policy. Выбран surface get_context/simulate/propose_plan/get_plan/prepare_action/start_job/get_job/cancel_job/get_action_status; экспорт по мере реализации.

MCP — вход для внешних ассистентов, ModelProvider — отдельный исходящий inference контракт. Принятая долгая команда возвращает cloud job id; transport disconnect не отменяет её. Approval создаёт доверенный UI/серверный путь, а не tool proposal модели.

## Проверка

Выбрать и проверить совместимый authorization server, pinned protocol/client matrix; real client conformance, audience/owner checks, expiry/revoke, state resume и отключение клиента. Unsupported capabilities возвращают явную ошибку.

Статус DECIDED означает выбранный проект, не работающий endpoint. [INTEGRATIONS](../INTEGRATIONS.md).
