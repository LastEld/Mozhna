# Облачный запуск

Подготовлены [Dockerfile](../Dockerfile), [compose.yaml](../compose.yaml), [render.yaml](../render.yaml) и Alembic. Ресурсы пока не созданы: нет размещённого URL, provider keys или подтверждённого бюджета. [Состояние alpha](IMPLEMENTATION.md).

## Render

Blueprint создаёт web API со статическим React, два background workers (исполнитель и scheduler) и PostgreSQL 17 в Frankfurt. БД не открыта публичному интернету. Выбраны starter services и минимальный платный database plan; фактическую стоимость показывает Render перед созданием. Автоматическое развёртывание последующих commits выключено (`autoDeployTrigger: off`). Формат сверён с [официальной спецификацией Render](https://render.com/docs/blueprint-spec).

1. Подключите Render к репозиторию LastEld/Mozhna и создайте Blueprint из корневого `render.yaml`.
2. Просмотрите список ресурсов и стоимость, задайте собственный `MOZHNA_PASSWORD` ≥16 символов.
3. Web pre-deploy выполняет `alembic upgrade head`. Worker/scheduler ждут актуальную migration до пяти минут, затем начинают работу. Если стартовая миграция дольше, перезапустите их после успешного release.
4. API берёт HTTPS origin из Render `RENDER_EXTERNAL_URL`. Для собственного домена явно задайте `PUBLIC_ORIGIN` равным адресу приложения без завершающего `/`.
5. Проверьте `/healthz`, вход, ручной snapshot, job с закрытой вкладкой и повторный вход с другого устройства.
6. Настройте backup/restore и наблюдение за failed/queued jobs до использования значимых данных.

Render подключён; создание ресурсов, smoke через внешний HTTPS и restore не выполнены. Blueprint не доказывает успешное размещение.

## Конфигурация

DATABASE_URL приходит из managed PostgreSQL. `MOZHNA_ENV=production` включает Secure cookie и проверку HTTPS/password. API работает в одном экземпляре: локальный limiter ещё не рассчитан на distributed auth.

Модели изначально выключены. Чтобы включить, на API и worker задайте выбранные API key/model переменные и разрешение metered inference из [RUNNING](RUNNING.md). Используйте billing limits провайдера; число jobs не является денежной квотой. MCP включается отдельным токеном только на API, не через пароль владельца.

Новые provider requests могут обрабатываться за пределами региона приложения. S3, OIDC, OCR, bank sync и внешние callbacks в alpha не используются и не создаются blueprint.

## Релиз и откат

Запускайте Runtime CI до deployment: migrations, pytest, contract drift, frontend, image, HTTP smoke. Первый запуск образа на Render требует отдельной проверки самого хостинга и мобильного интерфейса. Текущий SHA развёрнутого образа нужно фиксировать в release evidence.

Перед миграцией сохраните backup. Миграции применяются release task, а не каждым replica. Откат контейнера не означает безопасный downgrade БД. При восстановлении остановите worker/scheduler и убедитесь, что восстановленная queued/running job не повторит нежелательный платный вызов. Внешняя отправка отсутствует во всех текущих handlers.

Локальный Compose — отдельный режим с HTTP на loopback, не production-конфигурация. Подробности: [RUNNING](RUNNING.md), [OPERATIONS](OPERATIONS.md).
