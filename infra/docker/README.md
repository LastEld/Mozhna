# Container contract

Один backend image: собранные React assets, Python API и код worker/scheduler. Multi-stage build отделяет Node/frontend build от Python runtime; service process выбирается реальным entrypoint после реализации.

Money не требует модели/сети. API liveness/readiness и worker/scheduler heartbeat проверяются отдельно. Filesystem контейнера временный; данные в PostgreSQL/object storage.

Dockerfile, compose для local development и lockfiles добавляются в CLOUD-01 после проверяемого запуска, не как документационные заглушки. См. [STACK](../../docs/STACK.md).
