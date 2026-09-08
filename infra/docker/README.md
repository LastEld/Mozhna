# Контейнер

[Dockerfile](../../Dockerfile) собирает React на Node 24 и Python backend с frozen lockfile. Runtime работает непривилегированным пользователем. Один image используется для API, worker и scheduler. [compose.yaml](../../compose.yaml) добавляет PostgreSQL 17, release migration и persistent volume.

Инструкции: [RUNNING](../../docs/RUNNING.md). CI собирает image и проверяет health, frontend, защищённый API и Secure cookie. На локальном исполнителе Docker отсутствует; локальная успешная сборка Vite не подменяет проверку контейнера.
