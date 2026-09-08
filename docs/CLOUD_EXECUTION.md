# Действия в облаке

Статус: целевой контракт. В alpha реализован ограниченный SQL jobs/lease/scheduler; полный state machine, денежные квоты и мандаты остаются backlog. [Реальное покрытие](IMPLEMENTATION.md). Главный инвариант: после успешной постановки job закрытие клиента не уничтожает задачу.

## Путь команды

1. Backend проверяет identity, scope, command schema, версии и idempotency key.
2. В одной транзакции сохраняет изменение и job/outbox. Сетевые вызовы в этой транзакции не выполняются.
3. REST возвращает 202 + job_id; MCP возвращает короткий структурированный результат с тем же job_id. Ни один UI не держит HTTP-запрос открытым до конца поиска.
4. Worker забирает доступную запись короткой транзакцией с row lock/SKIP LOCKED, устанавливает lease и attempt token, освобождает lock.
5. Выполняет ограниченный шаг, сохраняет checkpoint/result с проверкой актуального attempt token.
6. Клиент читает job status; SSE — ускорение обновлений, polling — обязательный fallback.
7. Окончание создаёт notification outbox. Повторная доставка уведомления не исполняет действие заново.

## Job contract

Поля: id, owner_id, kind, command_version, payload_ref/hash, snapshot/plan_version, state, next_step, scheduled_at, lease_until, attempt_token, attempt_count, max_attempts, idempotency_key, deadline, budget, cancellation_requested, result_ref, error_code, created_at, updated_at.

| State | Смысл |
| --- | --- |
| QUEUED | Команда принята и ждёт исполнения |
| RUNNING | Конкретная попытка владеет lease |
| WAITING_APPROVAL | Требуется конкретное пользовательское разрешение |
| WAITING_INPUT | Не хватает подтверждённых данных |
| WAITING_PROVIDER | Provider временно недоступен; retry не вышел за бюджет |
| WAITING_EXECUTOR | Выбран внешний исполнитель и не доступен |
| PAUSED_BUDGET | Стоимость/лимит исчерпаны; платный fallback не включён |
| SUCCEEDED | Результат сохранён |
| FAILED | Известная конечная ошибка |
| CANCELED | Исполнение прекращено до дальнейших шагов |
| OUTCOME_UNKNOWN | Неизвестен результат внешней записи; требуется reconciliation |

Job и Action — разные state machines. Успешное создание draft не значит отправленный отклик. Состояние job, оборачивающего submit, согласуется с Action receipt.

## Повторы и параллельность

Чтения и чистые расчёты допускают ограниченный exponential backoff с jitter. Retry budget включает число попыток, deadline, provider quota и деньги. Один недоступный provider не блокирует все очереди.

Lease heartbeat не гарантирует отсутствие старого worker после сетевого разделения. Attempt token защищает запись результата от устаревшей попытки. Для внешних действий применяются дополнительный action lock/уникальность и повторная проверка mandate перед dispatch. Просроченный lease на уже начатом submit не разрешает автоматическую повторную отправку.

HTTP timeout, потерянный model stream и ошибочный tool output нормализуются. При неизвестном внешнем исходе сначала сверка. Отмена и смена модели не обнуляют число попыток, бюджет или использованные approvals.

## Расписания

Облако хранит Schedule(owner, timezone, recurrence, next_due_at, consent_ref, policy_version). Scheduler создаёт уникальную job по schedule_id + scheduled_for; несколько scheduler instances не создают дубликаты.

Правило календарного времени использует IANA timezone пользователя; переходы DST и пропущенные окна определены до включения расписания. По умолчанию missed runs сжимаются до одного актуального запуска, а не серии старых запросов. Нет привязки к таймеру в Android/iOS.

Примеры будущих задач: обновить разрешённый источник, пересчитать изменившийся денежный snapshot, проверить результат плана, найти вакансии в пределах read-мандата. Падение баланса без такого мандата создаёт предложение, а не вход на сайты.

## Отмена и возврат

`cancel_job` — явная серверная команда. Закрытие вкладки или разрыв SSE/MCP-запроса не равны отмене ранее принятой job. После cancellation worker прекращает новые шаги и пытается отменить model request; уже выполненное внешнее действие отменой не стирается.

При возврате с другого устройства клиент получает серверную plan/job version. Для записи использует expected_version; конфликт даёт 409/reload, не silent last-write-wins. Approval после изменения данных становится stale.

При отзыве account/mandate неотправленные actions блокируются независимо от того, открыт ли клиент. Restore не оживляет старые разрешения: применяется [OPERATIONS](OPERATIONS.md).
