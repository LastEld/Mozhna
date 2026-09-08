# Эксплуатация облачного приложения

Runtime alpha создан; hosting ещё не развёрнут. Ниже отделены работающие механизмы от оставшихся эксплуатационных задач. [Карта реализации](IMPLEMENTATION.md), [развёртывание](DEPLOYMENT.md), [backup/restore runbook](RECOVERY.md).

## Долговечность

PostgreSQL хранит финансовые records, jobs, schedules, sessions и owner_state. Sessions, лимит входа и jobs не зависят от памяти одного API-процесса. Отдельных outbox/approvals, object storage и приватных uploads в alpha пока нет.

Worker получает lease на 120 секунд. После аварии задание может быть повторено, до трёх attempts. CAS не даёт устаревшему worker перезаписать результат, но повторный provider request может тарифицироваться. Ошибка provider завершает job как failed; автоматического fallback или гарантии exactly-once нет. Worker и scheduler принимают SIGTERM/SIGINT: заканчивают текущую операцию и не начинают следующую. Оператор должен дать им время завершиться; принудительный kill хостинга остаётся возможным.

Scheduler сохраняет next_due, объединяет пропущенные интервалы и проверяет расписание под блокировкой владельца перед enqueue. Удаление данных сериализовано с записывающими API-запросами и scheduler. После logout/erase уже аутентифицированный, но ещё не записавший запрос повторно проверяет сессию перед изменением.

## Наблюдаемость

`/healthz` проверяет доступность таблиц/столбцов; в production — также соответствие Alembic head. Это readiness API, а не heartbeat worker или доказательство работоспособности модели.

UI показывает последние jobs, статусы, attempts и нормализованные ошибки; состояние хранится в БД. Отдельная система алертов и метрик ещё не настроена. До использования значимых данных нужны:

- API errors/latency, queue age, lease expiry и scheduler lag.
- Worker/scheduler heartbeat и оповещение о failed jobs.
- Контроль свежести snapshot и причин UNKNOWN.
- Расходы hosting/inference и billing limits провайдеров.
- Контроль успешного backup, retention и регулярная проверка restore.

Не помещайте в logs и traces выписки, CV, фото, provider tokens или полный model context. Корреляционные ID, audit ledger и унифицированное редактирование traces остаются будущей работой.

## Восстановление

[RECOVERY](RECOVERY.md) содержит команды backup, восстановления в новую БД, migration и `python -m mozhna.recovery --runtime-stopped`. До карантина должны быть остановлены API, worker и scheduler. Карантин сохраняет финансовые records, отменяет восстановленные queued/running jobs и удаляет schedules/sessions. Пароль и MCP bearer в окружении не меняются.

SQLite-проверка и реальный PostgreSQL dump/restore с карантином прошли [Runtime CI](https://github.com/LastEld/Mozhna/actions/runs/34274462396/job/102223924649) на commit `f6993d5cb933bfa7c3b85a28118e0beca83fb5c8`. Проверки восстановления на Render не было; RPO/RTO и retention не выбраны. Успешное создание backup не считается успешным restore.

## Ошибки и релизы

Ошибка денежных инвариантов приводит к UNKNOWN, а не разрешающему ответу. Недоступность модели не отключает деньги и планы. Cancel запрещает сохранение результата в canceled job, но не отзывает уже начавшийся сетевой запрос. Закрытие вкладки не останавливает работающий cloud worker.

Миграции выполняются отдельной release task. Production readiness отклоняет неактуальную схему; worker/scheduler startup ждёт migration head. Откат image не означает безопасный downgrade БД. Сохраните backup перед migration и проверяйте совместимость процессов при rollout. Изменение model ID требует разрешённого live smoke с доступным аккаунтом; mock contract test не заменяет его.

## Бюджет и границы

Paid inference изначально выключен. До 40 пользовательских jobs/24 часа и 1200 output tokens на вызов — ограничения нагрузки, не monetary budget reservation. Входные tokens и повторы после аварии могут оплачиваться; расходы надо ограничить у провайдера до включения.

Учитывайте API, worker, scheduler, БД и inference. Render Blueprint использует платные компоненты; ресурсы ещё не созданы. Персональные billing limits, alerting и cost accounting остаются открытыми.

Внешние отправки, банковские платежи, approvals, мандаты и OUTCOME_UNKNOWN для сторонних действий пока не реализованы. Их recovery/receipt/reconciliation policy нужно проверить до появления соответствующего executor.
