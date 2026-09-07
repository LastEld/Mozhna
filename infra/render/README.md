# Render target

Выбранная reference topology: Frankfurt web service (API + web assets), worker, scheduler и managed PostgreSQL в одном регионе. Ресурсы отсутствуют.

Во время CLOUD-01/DEPLOY-01 создать проверенный blueprint по реальным image/entrypoints, sizing и бюджету. Окружения и secrets раздельны; free-tier sleep не является основанием для постоянно работающего scheduler.

Файлы — private S3 bucket eu-central-1 при появлении uploads. См. [DEPLOYMENT](../../docs/DEPLOYMENT.md).
