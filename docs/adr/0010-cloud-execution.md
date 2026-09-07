# Долговечное облачное выполнение

Статус: DECIDED. Дата: 2026-09-07. Основание: работа в облаке независимо от открытого клиента; [CONTEXT](../CONTEXT.md).

## Решение

Job/outbox и command фиксируются одной PostgreSQL транзакцией. Worker/scheduler — отдельные процессы общего backend image. Lease, attempt token, checkpoints, cancellation, budget и scoped context сохраняются в БД. Scheduler дедуплицирует schedule_id + due_at.

Повторы внешнего submit разрешаются только после выяснения предыдущего исхода. OUTCOME_UNKNOWN сохраняется; локальная уникальность команды не обещает exactly-once чужого API. Устройство лишь читает прогресс и выдаёт явные команды.

## Проверка

Worker restart и lease expiry, два consumer/scheduler, закрытый телефон, explicit cancel, изменённый approval, восстановление backup и provider outage. C0 обязан продемонстрировать durable job прежде, чем она называется облачной автоматизацией.

Полный контракт: [CLOUD_EXECUTION](../CLOUD_EXECUTION.md).
