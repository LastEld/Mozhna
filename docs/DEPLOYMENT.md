# Целевое облачное развёртывание

Статус: выбрана reference-топология, ресурсы не созданы и платные планы не подключены.

## Первый hosting target

**Render, Frankfurt:** Docker web service для API + production React assets, отдельные Python background worker и scheduler, managed PostgreSQL в том же регионе. **Amazon S3, eu-central-1:** приватные файлы при появлении uploads. До чеков bucket не требуется.

Render поддерживает непрерывные background workers и Frankfurt region; private network региональная. Это соответствует выбранной форме API/worker/database, но не гарантирует конкретный SLA нашего приложения. [Workers](https://render.com/docs/background-workers), [Regions](https://render.com/docs/regions). Регион S3 подтверждается [AWS endpoints](https://docs.aws.amazon.com/general/latest/gr/s3.html).

Первое развёртывание использует постоянно работающие процессы, без обязательной зависимости от free-tier sleep. Конкретный тариф и месячный бюджет определяются перед созданием ресурсов. Отдельный worker, scheduler и managed database имеют эксплуатационную стоимость; документация её не скрывает и не придумывает цену.

Docker, PostgreSQL и S3 API позволяют перенести приложение на другой container host без переписывания домена. Render-specific configuration живёт в infra/render; она не импортируется Money или LLM adapters.

## Публичная и приватная границы

Один публичный origin, HTTPS: web, /api/v1, /mcp, auth callbacks и validated webhook endpoints. Worker/scheduler/database не получают публичный пользовательский ingress. Object bucket приватный, доступ через краткоживущие scoped links.

Authentication provider должен поддерживать web OIDC и требуемый MCP authorization flow; его совместимость проверяется в C0. Не писать собственный OAuth authorization server ради быстрого demo. Выбор конкретного identity service остаётся deployment prerequisite, не выбором языка/архитектуры.

Bank/LLM providers могут обрабатывать данные за пределами выбранного hosting региона; Frankfurt не означает автоматическое EU-only движение всех данных. Connector registry содержит фактические ограничения разрешённой обработки.

## Окружения и конфигурация

Local/test используют синтетические данные, staging — отдельные DB/secrets/bucket, production — отдельные identity client и budgets. PR previews не получают production credentials.

Конфигурационные группы: DATABASE_URL, PUBLIC_ORIGIN, OIDC_ISSUER/CLIENT_ID/secret reference, MCP_RESOURCE/AUTHORIZATION_SERVER, OBJECT_STORAGE endpoint/bucket/region, MODEL_PROVIDER registry/secret references, inference/task budgets, schedule timezone policy, retention и observability settings. Это список требований, не готовый .env.

Secrets находятся в cloud secret storage/env injection, не в Vite public variables, repo, prompts или raw logs. BYOK и provider sessions шифруются ключом отдельно от пользовательских данных.

## Сборка и релиз

C0 создаёт реальные Dockerfile, lockfiles и проверенные entrypoints для api/worker/scheduler. Пока этих файлов нет, blueprint и fake start commands не публикуются.

CI после реализации: Python lint/tests, TypeScript check/build, schema/client drift check, browser critical paths и image build. Миграции Alembic запускаются отдельной release task; не каждым replica при старте. Применяется expand/contract, чтобы старые worker и UI пережили rollout.

Backend image закрепляется digest. Health: liveness процесса, readiness зависимостей, worker heartbeat и scheduler lag. Откат image не откатывает миграцию данных автоматически.

Релиз проверяет: задача пережила restart worker; браузер можно закрыть; модель недоступна без потери планов; два устройства видят одну версию; внешние действия не повторились. Дальнейшие правила: [OPERATIONS](OPERATIONS.md).
