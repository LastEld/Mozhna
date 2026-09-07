# Runtime и первый облачный срез

Статус: DECIDED. Дата: 2026-09-07. Выбор выполнен исполнителем по прямому поручению владельца: облачное действие, подходящие языки, разные LLM и устройства. Основание: [CONTEXT](../CONTEXT.md).

## Решение

Python/FastAPI/Pydantic backend, SQLAlchemy/Alembic/PostgreSQL, TypeScript/React/Vite PWA. Один backend image запускает отдельные API, worker и scheduler. Money — чистый внутренний domain module. PostgreSQL хранит долговечное состояние, jobs/outbox; приватные файлы — object storage.

Первый срез — cloud foundation и manual money. Remote MCP и LLM adapters входят в раннюю техническую архитектуру; банковская интеграция не нужна для их existence. Product gates и спорные финансовые политики остаются отдельными решениями.

## Причина и последствия

Облако должно продолжать работу после закрытия устройства и давать тот же план другому клиенту/модели. Ручной money path сохраняет минимальность проверки продукта. Два языка требуют generated TypeScript client из OpenAPI и contract CI.

Render Frankfurt выбран reference host; Docker/PostgreSQL/S3 сохраняют возможность миграции. Ресурсы/бюджет/deployment ещё не созданы. Более ранний статус «выбрать framework/языки» заменён этим поручением; это не принятие всех предложений v2.

Проверка: [BACKLOG](../BACKLOG.md), CLOUD-01/JOB-01/DEVICE-01 и [STACK](../STACK.md).
