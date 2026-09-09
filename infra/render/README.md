# Render Free test

Корневой [render.yaml](../../render.yaml) содержит один Free Python web service и Free PostgreSQL 17 в Frankfurt. API, worker и scheduler работают отдельными процессами в одном экземпляре. Auto-deploy выключен; paid inference запрещён.

При idle-сне web фон останавливается; PostgreSQL истекает через 30 дней. Владелец подтвердил бюджет €0 и отсутствие привязанной банковской карты в `My Workspace` 2026-09-09. Free compute само по себе не запрещает списания за превышение трафика при наличии платёжного метода; без него превышение лимитов приостанавливает сервисы/сборки. [Запуск и ограничения](../../docs/DEPLOYMENT.md).

Migrations выполняются supervisor до запуска API/worker/scheduler. Free PostgreSQL `mozhna-test-db` (`dpg-dagl972d0e5s73cvums0-a`) уже создана в Frankfurt: PostgreSQL 17, внешний доступ закрыт (`ipAllowList: []`), истечение 2026-10-09 в 12:44:12 UTC. Free web `mozhna-test` (`srv-dagl9tid0e5s73d01c8g`) тоже создан; сборка commit `1596a5583bf46be125e4208a99e6e2883e160f39` прошла, runtime остановлен из-за незаполненного `DATABASE_URL`. Перенесите Internal Database URL из Dashboard БД в Environment сервиса и выполните deployment по инструкции выше. HTTPS smoke пока не выполнен. Не создавайте дубликаты существующих ресурсов через Blueprint.
