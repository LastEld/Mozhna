# Модель данных

Логический контракт облачного состояния, не готовые таблицы или миграции. Каждая пользовательская сущность принадлежит owner/workspace; проверки владения обязательны и в личном pilot.

| Область | Сущности | Правило |
| --- | --- | --- |
| Владение | User, Workspace, Membership | Scope выводится из проверенной identity |
| Источники | Evidence, EvidenceRevision | Тип, ссылка, observed_at, quality, privacy, supersedes |
| Деньги | Account, BalanceSnapshot, Transaction, Annotation, ReceiptLink | Исходное наблюдение отделено от пользовательской трактовки |
| Планирование денег | Commitment, IncomeExpectation, ReservePolicy, Goal, BudgetAllocation | Даты и версии обязательны; один расход не резервируется дважды |
| Расчёты | Calculation, SpendDecision | Snapshot, policy, inputs и объяснение воспроизводимы |
| Reduce | Need, Baseline, Alternative, Microcontract, OutcomeObservation | Потенциал, принятие и факт различаются |
| Earn | CareerProfile, ProfileFact, JobOpportunity, ApplicationDraft | Факт профиля имеет provenance, объявление — источник и дату проверки |
| Внешние действия | ActionIntent, Approval, Mandate, Attempt, ExternalReceipt | Payload и разрешение связаны версиями и hash |
| Подключения | Connection, CapabilityManifest | Secret reference вместо секрета в прикладном ответе |
| Задания | Job, OutboxEvent, Schedule | Lease, attempt token, idempotency, checkpoints, timezone, ожидание и последняя ошибка |
| Модели | ModelProviderConfig, CapabilitySnapshot, ModelRun, BudgetReservation | Разрешённый model id, schema/version, usage, лимит, source refs и нормализованная ошибка |
| Клиенты | DeviceSession, NotificationSubscription, InboxItem | Отзыв сессии, opt-in, delivery state; устройство не владеет единственной копией плана |

Cloud Plan/PlanVersion хранит typed spending-change и income-search планы между устройствами и моделями. Это простой доменный контейнер, не универсальный workflow engine.

История изменений не доказывает истинность внешнего источника и не защищает от администратора базы сама по себе. Обычные операции не переписывают исходные события; политика удаления/retention применяется также к истории, файлам и backups.
