# Облачная инфраструктура

Reference target: Render Frankfurt — API/web, worker, scheduler и managed PostgreSQL; приватное S3 eu-central-1 для файлов. Ресурсы и платные планы сейчас не созданы.

[DEPLOYMENT](../docs/DEPLOYMENT.md) описывает topology, identity prerequisite, окружения и release pipeline. Dockerfile и Render blueprint появятся вместе с рабочими entrypoints/lockfiles; фиктивные deploy commands не добавляются.

infra/render содержит target-specific инструкции, infra/docker — контракт образа. Secrets, реальные базы, Terraform state и browser sessions не коммитятся. Деньги/планы не зависят от SDK cloud host.
