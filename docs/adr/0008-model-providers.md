# Сменные LLM providers

Статус: DECIDED. Дата: 2026-09-07. Основание: поручение адаптировать MOZHNA к разным LLM; [CONTEXT](../CONTEXT.md).

## Решение

Один Python ModelProvider port; adapters нормализуют capabilities, request/result, schema errors, usage, timeout/cancel/refusal. Первые adapters Anthropic и Gemini; затем OpenAI и проверенные self-hosted endpoints. Provider/model IDs — runtime registry.

Router детерминированный: разрешённые данные/region, capabilities, budget и priority list. Fallback только разрешённый, не меняет права/план и не обходит refusal. Каноническое состояние не зависит от conversation id модели.

## Последствия

Нет универсального обещания равных tool/vision/JSON возможностей. Adapter conformance общий, live proof нужен на двух providers. Без разрешённого inference endpoint cloud job явно ожидает настройки; подписочный клиент доступен отдельно по MCP.

Полный контракт: [LLM_ADAPTERS](../LLM_ADAPTERS.md).
