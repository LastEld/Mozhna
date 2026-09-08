# Проверка качества и BaseLineReduce

## Протокол

До реализации нового механизма записать TargetOutcome, StrongBaseline, MinimalIntervention, Gain, OffTargetDamage, Applicability, KeepGate, StopGate и Ablation. После наблюдений выбрать KEEP, REDUCE, REWORK или STOP и приложить данные.

Baseline — банк/ручной импорт, калькулятор или таблица и существующий AI-harness с теми же исходными данными. Сравнение только с отсутствием действий недостаточно.

Исходный BR-0: 7 дней наблюдений и минимум 20 реальных вопросов. Это дизайн измерения, не дедлайн разработки. В BR-1 исходные ориентиры: медиана времени до ответа ≤10 секунд, ≥60% проверок полезнее калькулятора, опасные ложные CAN не хуже baseline. Историческое требование ≥95% воспроизводимости полевых ответов не заменяет строгую инженерную воспроизводимость: одинаковые входы и policy должны всегда давать одинаковый результат.

Ранние документы предлагают +15 п.п. для поведенческих механизмов, v2 предлагает метрики по способности. Это расхождение не разрешено автоматически. Протокол и знаменатель фиксируются до эксперимента; порог после результата не меняется.

## Разные виды доказательств

| Утверждение | Проверка |
| --- | --- |
| Верная арифметика | Контрольные cases, инварианты, replay |
| Полезность ручного продукта | Сопоставимые реальные проверки против baseline |
| Исполнимая экономия | Фактические расходы, объём, остатки, отходы, усилия и ограничения |
| Польза Earn | Приемлемые вакансии, время человека, ответы/интервью отдельно |
| Корректные права | Чужой owner, изменённый payload, expiry, revoke, prompt injection |
| Надёжное исполнение | Timeout, lost response, duplicate command и restore |

## Облачная и адаптивная приёмка

- Принятая job завершается при закрытой вкладке; restart worker продолжает сохранённый шаг.
- Два workers/schedulers не дублируют команду; устаревший attempt не перезаписывает результат.
- Один план продолжается с ПК на iPhone и с одной LLM на другой; owner/version/budget сохраняются.
- API и MCP одинаково отказывают чужому owner и stale write.
- Два реальных model providers проходят общий schema/permission contract; fake adapter не доказывает интеграцию.
- Provider outage, quota, refusal и malformed output сохраняют факты и права; cloud cost limit не обходится fallback.
- Реальные iPhone/Safari, Android/Chrome и ПК проходят критические пути; CI WebKit не заменяет устройство.
- Без push/установки и при reconnect основные сценарии доступны; offline не выдаёт новый CAN из stale snapshot.

Подробности: [CLIENTS](CLIENTS.md), [LLM_ADAPTERS](LLM_ADAPTERS.md), [CLOUD_EXECUTION](CLOUD_EXECUTION.md).

## Обязательные сценарии

- Баланс уже включает pending; не вычесть снова.
- Чек, ручная запись и банк описывают одну покупку.
- Кредитный лимит не является собственными деньгами.
- Оплаченные продукты уменьшают оставшийся бюджет жизни.
- Неполный snapshot даёт UNKNOWN, но не блокирует независимое сравнение цен.
- Упаковка дешевле за месяц, но недоступна по текущим деньгам.
- Непринятая экономия не меняет баланс или подтверждённый план.
- Новый CV делает approval устаревшим.
- Потерянный ответ на submit не вызывает слепой повтор.
- Restore не оживляет отозванные права.

Для кода проверять реальную границу: API/MCP клиент, транзакция базы, adapter и worker там, где риск находится. Mock-only проверка хендлера не доказывает работающую интеграцию.

Runtime CI предыдущей alpha проверил pytest, PostgreSQL, реальный MCP HTTP client, migrations, frontend, drift и container smoke. В текущий срез добавлены гонки auth/erase/scheduler, реальный PostgreSQL dump/restore с карантином, Vitest для точных cents и Playwright для Desktop Chrome, Pixel 7/Chromium и iPhone 13/WebKit. На commit `f6993d5cb933bfa7c3b85a28118e0beca83fb5c8` [Runtime verify](https://github.com/LastEld/Mozhna/actions/runs/34274462396/job/102223924649) прошёл: 65 backend tests без пропусков, 10 frontend tests, production build, PostgreSQL dump/restore, migrations, contract drift, Docker build и production HTTP smoke. Браузерный прогон aee31f7b дал 5 успешных тестов и 1 сбой offline reload WebKit. Теперь этот сценарий отделён и исполняется как ожидаемый сбой `WEBKIT-OFFLINE-01`; полный offline gate остаётся открытым. Live model calls, real-device QA, облачный restore и полевые продуктовые исследования не проводились. [Карта доказательств](IMPLEMENTATION.md).
