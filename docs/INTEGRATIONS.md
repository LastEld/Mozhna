# Интеграции облачного MOZHNA

Ни одна интеграция пока не подключена. Каждый adapter имеет owner/consent, capability manifest, health и проверенный контракт. Секреты доступны облачному executor/provider adapter, а не устройству пользователя или модели.

## Банк и чеки

BankDataProvider: accounts, balance snapshots, transactions, cursor, consent state, freshness и capabilities. Первый банк только read-only. Adapter описывает booked/available/pending и проходит сценарии повторов, переводов, возвратов и расхождений.

CSV — baseline, банк устраняет ручной ввод. Cloud upload принимает приватный файл; worker извлекает данные/OCR/vision через разрешённую capability и создаёт предложение связи с транзакцией. Неуверенные поля подтверждаются; чек не становится вторым платежом. Формат/размер ограничены, retention задан, ссылки короткоживущие.

Камера на устройстве — progressive enhancement: всегда остаётся file picker. Обработка чека продолжается после закрытия клиента.

## Telegram

Группа получает только разрешённое уточнение; @-упоминание запускает проверку user id, chat id и MOZHNA owner. Упоминание не выдаёт authentication/approval.

Webhook аутентифицируется, дедуплицируется по provider event id и ставит cloud job. Минимальное уведомление ведёт в личный интерфейс; баланс, CV и полный чек по умолчанию не раскрываются. Критичные approvals проходят доверенный личный UI с актуальной версией.

## Входящий remote MCP

Выбран HTTPS Streamable HTTP endpoint `/mcp`. Протокольную версию и supported client versions фиксировать в compatibility matrix при реализации; не объявлять поддержку всех клиентов по одному успешному тесту. Standard transports и OAuth описаны в [MCP transport](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports) и [authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization).

| Tool | Действие | Scope / эффект |
| --- | --- | --- |
| get_context | Минимальный context по задаче и версии | Read; фильтруется по owner и разрешённым данным |
| simulate | Детерминированный расчёт сценария | Compute; не меняет утверждённые данные |
| propose_plan | Сохранить typed предложение | Draft write, idempotency key |
| get_plan | План, версии, следующий шаг и наблюдения | Read |
| prepare_action | Создать конкретный draft intent | Draft write; не подтверждение |
| start_job | Поставить allowlisted cloud command | Scopes нужного job kind и проверенный consent |
| get_job | Состояние и результат job | Owner-scoped read |
| cancel_job | Запросить остановку дальнейших шагов | Owner-scoped command |
| get_action_status | Реальный action outcome | Read, без повторного dispatch |

Это выбранный проектный surface, пока не реализованный API. В C2 экспортируются только реально работающие capabilities; будущие tools не изображаются no-op заглушками.

Web approval подтверждает конкретный payload и ставит dispatch job серверным путём. Отдельного произвольного submit tool для модели нет. Model response или start_job не выпускают approval и не обходят [ACTIONS](ACTIONS.md).

Token предназначен ресурсу MOZHNA; provider token не проксируется. Сессия/транспорт MCP не является хранилищем плана. Долгая операция возвращает job id; разрыв запроса не удаляет принятую cloud job. См. [CLOUD_EXECUTION](CLOUD_EXECUTION.md).

## Исходящий LLM доступ

Cloud worker использует отдельный ModelProvider port с capability checks, budget reservation и нормализованным результатом. Anthropic/Gemini — первые adapters; OpenAI и проверенные self-hosted endpoints добавляются без изменения Money и Plan. [LLM_ADAPTERS](LLM_ADAPTERS.md) — полный контракт.

Внешний подписочный AI-клиент может пользоваться MCP отдельно. Он не заменяет облачные inference credentials и не нужен для непрерывной работы настроенного provider.

## Вакансии и аккаунты

L0 — public search; L1 — scoped account read; L2 — draft; L3 — confirmed submit; L4 — отдельный будущий mandate. OAuth или разрешённый browser-auth без передачи паролей/2FA модели. MFA/истёкшая сессия переводит job в WAITING_INPUT; облачный процесс не обходит проверку.

Manifest: search/read/draft/submit/receipt verification, supported auth, last validated. Отсутствующая capability отключена. Фильтры сначала жёсткие; salary/net income/право на работу не выдумываются, fit score не называется вероятностью оффера.

## Deployment prerequisites

Конкретный bank provider и job connector; OIDC/MCP authorization server; доступные модели/keys и лимиты; поля Telegram и consent. Выбор cloud stack уже сделан. Эти подключения выполняются перед соответствующими live tests, не мешают реализации чистых контрактов и manual cloud money.
