# Render Free test

Корневой [render.yaml](../../render.yaml) содержит один Free Python web service и Free PostgreSQL 17 в Frankfurt. API, worker и scheduler работают отдельными процессами в одном экземпляре. Auto-deploy выключен; paid inference запрещён.

При idle-сне web фон останавливается; PostgreSQL истекает через 30 дней. Для строгого €0 нужна подтверждённая конфигурация биллинга без платёжного метода: Free compute само по себе не запрещает списания за превышение трафика. [Запуск и ограничения](../../docs/DEPLOYMENT.md).

Migrations выполняются supervisor до запуска API/worker/scheduler. Ресурсы ещё не созданы.
