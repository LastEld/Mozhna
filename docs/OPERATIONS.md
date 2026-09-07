# Эксплуатация облачного приложения

Статус: требования и план; runtime/hosting ещё не созданы. Target описан в [DEPLOYMENT](DEPLOYMENT.md).

## Долговечность

PostgreSQL хранит facts, plan versions, jobs, outbox и approvals. Приватные файлы — object storage. API replicas не хранят единственную копию session/job state в памяти. Worker restart продолжает checkpoint; scheduler не зависит от устройства пользователя.

Backup/restore покрывает базу, файлы и metadata связи, но не раскрывает секреты в export. Конкретные RPO/RTO и retention выбираются перед production исходя из бюджета и требований; успешное создание backup не считается проверкой restore.

## Наблюдаемость

| Сигнал | Назначение |
| --- | --- |
| API latency/errors и readiness | Доступность клиента/MCP |
| last_successful_sync, as_of | Свежесть денег |
| reconciliation difference, UNKNOWN reason | Качество финансового основания |
| Queue age, lease expiry, attempts | Потерянные/зависшие jobs и конкуренция |
| Scheduler lag и duplicate suppression | Исполнение расписаний |
| Provider timeout/refusal/quota | Состояние LLM/внешних connectors |
| Reserved/actual task cost | Бюджет inference и внешних действий |
| OUTCOME_UNKNOWN | Очередь обязательной сверки |
| Worker/scheduler heartbeat | Различать отсутствие задач и мёртвый процесс |

Logs: correlation ID, versions, error categories и минимальные причины. Нет raw выписок, CV, фото, provider tokens и model context по умолчанию. Secrets хранятся отдельно; traces редактируются по privacy policy.

## Восстановление

1. Остановить внешние dispatch и scheduler до проверки восстановленного состояния.
2. Восстановить DB/object links и проверить версию схемы/денежной policy.
3. Сверить active connections, revocation epoch, consent и неизвестные внешние исходы.
4. Старые approvals/мандаты, актуальность которых нельзя доказать, оставить недействительными; не оживлять по старому backup.
5. Восстановить read-only задачи и API; внешние actions разрешать только после reconciliation.
6. Зафиксировать фактический результат restore test.

Нельзя обещать exactly-once на произвольном job-сайте. Принятый работодателем отклик не отменяется восстановлением базы.

## Ошибки и релизы

Ошибка денежных инвариантов выключает зависимое разрешающее решение. Недоступность LLM сохраняет деньги/планы и ставит соответствующие задачи в ожидание. Потерянный submit response создаёт OUTCOME_UNKNOWN и блокирует автоматический повтор.

Миграция отдельной release task, совместимость старого frontend/worker на время rollout, image rollback без автоматического удаления новых данных. Изменение model version проходит adapter conformance и малый разрешённый smoke перед полным включением.

Клиентское отключение и транспортная отмена не отменяют уже принятую cloud job; явная cancel_job прекращает будущие шаги. Server-side cancellation/revoke проверяются независимо от online-статуса телефона.

## Бюджет

Учитывать web/API, workers/scheduler, DB, storage/traffic, inference и внешние providers. Первый production план должен иметь лимиты per-user/per-task/global и видимые паузы. Без настроенного inference provider фоновые LLM-задачи не объявляются работающими.
