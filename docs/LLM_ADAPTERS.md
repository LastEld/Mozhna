# Адаптация к разным LLM

Статус: выбранный контракт; Anthropic/Gemini adapters и mock contract tests реализованы; live tests, fallback и полный capability registry отсутствуют. [Alpha scope](IMPLEMENTATION.md).

## Две разные совместимости

| Направление | Контракт | Для чего |
| --- | --- | --- |
| MOZHNA → модель | ModelProvider | Worker в облаке самостоятельно вызывает inference |
| AI-клиент → MOZHNA | Remote MCP + те же application services | Пользователь использует свой привычный клиент и его модель |

MCP — не универсальная замена inference API. OpenAI-совместимый endpoint тоже не доказывает одинаковые capabilities всех моделей.

## Порт ModelProvider

`describe_capabilities()`, `generate(ModelRequest)`, `cancel(request_id)` — внутренний контракт; cancel допускает явное not_supported. Adapter нормализует ошибки, usage, provider_request_id и результат.

ModelRequest: task_kind, canonical context refs/version, permitted input data, output_schema_version, selected model_id, deadline, maximum output, reserved budget, request id. Tool proposals — только типизированные allowlisted команды; model response не является разрешением.

ModelResult: status, parsed output или text, tool_proposals, usage, finish_reason, provider_request_id, model_id, provider/version, validation_errors. Hidden reasoning не нужен для хранения состояния или продолжения задачи.

## Реестр возможностей

| Capability | Использование |
| --- | --- |
| text / image input | Получить текстовый контекст либо извлечь данные из разрешённого изображения |
| structured output + supported schema subset | Выбрать допустимую схему; всё равно выполнить Pydantic/domain validation |
| tool proposal support | Принять предложенную команду через серверную policy |
| streaming / cancellation | Улучшить UX; бизнес-результат остаётся в job |
| context/output limits | Ограничить payload и выбрать task-scoped context |
| data handling / allowed region | Не отправить данные запрещённому provider |
| pricing/quota / availability | Проверить бюджет и возможность запуска |
| last_verified + adapter version | Отличить проверенный контракт от предположения |

Отсутствие tools не мешает текстовой задаче. Отсутствие vision не маскируется: либо отдельное разрешённое OCR, либо другой разрешённый provider. Неструктурированный ответ можно разобрать и проверить с ограниченной повторной попыткой; если контракт не получен — INVALID_OUTPUT, без выполнения действия.

Structured outputs существуют у Claude и Gemini, но конкретные модели и поддерживаемые ограничения проверяются отдельно. Это не гарантия истинности содержания. [Claude](https://platform.claude.com/docs/en/build-with-claude/structured-outputs), [Gemini](https://ai.google.dev/gemini-api/docs/structured-output).

## Маршрутизация и переключение

Детерминированный порядок: разрешённые providers/region → необходимые capabilities → бюджет/deadline → явно заданный priority list. На первом этапе не строим обучаемый router и не используем другую LLM для выбора LLM.

У каждой задачи собственный профиль: receipt_extract, alternative_proposal, job_summary, application_draft. Результат смены модели проверяется той же схемой и теми же domain-инвариантами. Смена модели не меняет пользователя, финансовую policy, план или разрешение.

Fallback разрешён только внутри согласованного списка и лимита. Чувствительные данные не пересылаются другому provider молча. Rate limit допускает retry; invalid credentials блокируют connection; safety refusal не запускает цепочку обхода отказа. Invalid output допускает максимум ограниченные schema-repair попытки в общем бюджете.

До вызова резервируется бюджет с защитой от параллельного перерасхода; после usage уточняется фактическая стоимость. При неизвестной цене/стоимости используется консервативный резерв либо пауза. Billing не обещает точность до receipt провайдера.

## Начальный набор

Сначала реализовать Anthropic API adapter и Gemini API adapter; в cloud alpha один настраивается оператором, второй нужен для доказательства переключаемости. OpenAI adapter и явно проверенные self-hosted/OpenAI-compatible endpoints — расширения того же порта. Ни один provider/ключ этим документом не подключается.

Models IDs, цены и лимиты — deployment registry, не константы Money Kernel. Перед live smoke tests выбрать реально доступные модели и budget. До реального второго provider тесты с fake adapter доказывают только структуру, не multi-provider совместимость.

## Подписка и исполнители

Внешний ChatGPT/Claude Code может работать по собственной подписке как MCP-клиент, если его версия поддерживает нужный доступ. MOZHNA не извлекает подписочные cookies/tokens и не держит интерактивную сессию пользователя как облачный daemon.

Для фонового inference используется разрешённый API account, BYOK через secret storage или отдельно развёрнутый model endpoint. Self-hosted endpoint требует собственной инфраструктуры; его наличие не предполагается. При отсутствии provider приложение продолжает учёт, а model job явно ожидает настройку/исполнителя.

## Проверка

Общий conformance suite на adapters: valid schema, unsupported capability, context overflow, rate limit, timeout, cancellation, refusal, malformed tool proposal, unavailable pricing. Live gate: один task snapshot через два разных providers, валидный domain-result и одинаковые права; одинаковая формулировка текста не требуется.

Continuity gate: начать план через одну модель, закрыть клиент, продолжить через другую с той же cloud plan version. История чата провайдера не является единственным носителем плана.
