# Инфраструктура

Корневые [Dockerfile](../Dockerfile), [compose.yaml](../compose.yaml) и [render.yaml](../render.yaml) запускают API/web, worker, scheduler и PostgreSQL. [DEPLOYMENT](../docs/DEPLOYMENT.md) описывает переменные, миграции и cloud release; [RUNNING](../docs/RUNNING.md) — локальный запуск.

Ресурсы облака ещё не созданы. S3 добавится вместе с uploads; сейчас он не нужен. Секреты, реальные базы и sessions не коммитятся.
