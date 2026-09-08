# Облачный запуск

Подготовлены [Dockerfile](../Dockerfile), [compose.yaml](../compose.yaml), [render.yaml](../render.yaml) и Alembic. Ресурсы пока не созданы: нет размещённого URL, provider keys или подтверждённого бюджета. [Состояние alpha](IMPLEMENTATION.md).

## Render

Blueprint создаёт web API со статическим React, два background workers (исполнитель и scheduler) и PostgreSQL 17 в Frankfurt. БД не открыта публичному интернету. Выбраны starter services и минимальный платный database plan; фактическую стоимость показывает Render перед созданием. Автоматическое развёртывание последующих commits выключено (`autoDeployTrigger: off`). Формат сверён с [официальной спецификацией Render](https://render.com/docs/blueprint-spec).

1. Подтвердите workspace в Render connector: доступен `My Workspace`, но выбранного workspace пока нет. Connector требует явного выбора владельцем. Затем подключите Render к репозиторию LastEld/Mozhna и создайте Blueprint из корневого `render.yaml`.
2. Просмотрите список ресурсов и стоимость, задайте собственный `MOZHNA_PASSWORD` ≥16 символов.
3. Web pre-deploy выполняет `alembic upgrade head`. Worker/scheduler ждут актуальную migration до пяти минут, затем начинают работу. Если стартовая миграция дольше, перезапустите их после успешного release.
4. API берёт HTTPS origin из Render `RENDER_EXTERNAL_URL`. Для собственного домена явно задайте `PUBLIC_ORIGIN` равным адресу приложения без завершающего `/`.
5. Проверьте `/healthz`, вход, ручной snapshot, job с закрытой вкладкой и повторный вход с другого устройства.
6. Выполните [backup/restore drill](RECOVERY.md) и настройте наблюдение за failed/queued jobs до использования значимых данных.

Render подключён, workspace ещё не выбран, создание платных ресурсов не подтверждено. Создание ресурсов, smoke через внешний HTTPS и облачный restore не выполнены. Blueprint не доказывает успешное размещение. Доступный connector не создаёт эту Docker/worker topology целиком, поэтому подготовлен путь через Blueprint Dashboard.

## Конфигурация

DATABASE_URL приходит из managed PostgreSQL. `MOZHNA_ENV=production` включает Secure cookie и проверку HTTPS/password. Blueprint запускает один экземпляр API. Лимит входа и сериализация мутаций владельца хранятся в PostgreSQL, общие для процессов. Полное масштабирование и нагрузочные сценарии ещё не проверены.

Модели изначально выключены. Чтобы включить, на API и worker задайте выбранные API key/model переменные и разрешение metered inference из [RUNNING](RUNNING.md). Используйте billing limits провайдера; число jobs не является денежной квотой. MCP включается отдельным токеном только на API, не через пароль владельца.

Новые provider requests могут обрабатываться за пределами региона приложения. S3, OIDC, OCR, bank sync и внешние callbacks в alpha не используются и не создаются blueprint.

## Релиз и откат

Запускайте Runtime CI до deployment: migrations, pytest, PostgreSQL dump/restore, contract drift, frontend tests/build, Playwright, image и HTTP smoke. Новые браузерные и restore gates должны пройти именно на выбранном commit. Первый запуск образа на Render требует отдельной проверки самого хостинга и мобильного интерфейса. Текущий SHA развёрнутого образа нужно фиксировать в release evidence.

Перед миграцией сохраните backup. Миграции применяются release task, а не каждым replica. Откат контейнера не означает безопасный downgrade БД. При восстановлении остановите API, worker и scheduler, восстановите базу отдельно и выполните `python -m mozhna.recovery --runtime-stopped` до запуска процессов. Команда изолирует queued/running jobs, удаляет schedules и sessions; точная последовательность — в [RECOVERY](RECOVERY.md). Внешняя отправка отсутствует во всех текущих handlers.

Локальный Compose — отдельный режим с HTTP на loopback, не production-конфигурация. Подробности: [RUNNING](RUNNING.md), [OPERATIONS](OPERATIONS.md).
