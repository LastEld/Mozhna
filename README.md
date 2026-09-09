# MOZHNA / Можна

Облачный личный финансовый помощник: понять доступную сумму, проверить покупку, сравнить способы удовлетворить повторяющуюся потребность и сохранить результат.

**Тестовый бюджет: €0.** Render workspace — `My Workspace`; отсутствие привязанной карты подтверждено владельцем; Free web и PostgreSQL созданы. Фон засыпает вместе с web, тестовая PostgreSQL истекает через 30 дней. [Ограничения](docs/DEPLOYMENT.md).

**Alpha 0.1:** реализованы backend, адаптивный web-интерфейс, фоновые задания и инструкции запуска. Облачная сборка прошла, но приложение ещё не запущено: требуется заполнить `DATABASE_URL` в Render. [Завершить подключение](docs/DEPLOYMENT.md#продолжение-текущего-запуска). Это однопользовательская alpha; полный roadmap остаётся открытым. [Точное состояние и ограничения](docs/IMPLEMENTATION.md).

## Что уже есть

- Денежное ядро без LLM: ручной остаток, обязательства, резерв, цель, бюджет жизни и проверка покупки с `UNKNOWN` при неполных/устаревших данных.
- Планы экономии: сценарий, принятие/отказ, реальные наблюдения, стоимость запуска и ежедневный пересчёт.
- Журнал и CSV с защитой от повторного импорта; записи не увеличивают и не уменьшают остаток автоматически.
- Durable jobs: отдельные worker/scheduler, восстановление после истёкшего lease, отмена, ограничения очереди.
- Адаптеры Anthropic и Gemini для черновиков; ключи и разрешение платных вызовов задаются оператором. Live-вызовы пока не проверены.
- Remote MCP: четыре инструмента чтения с отдельным bearer-токеном, проверенные настоящим SDK-клиентом по HTTP. OAuth пока отсутствует.
- Вход владельца, серверные сессии, CSRF и общий для процессов лимит входа в БД. Повторная проверка сессии в транзакции защищает запись после удаления данных или выхода.
- JSON-экспорт и удаление данных; операторская команда изолирует задания, расписания и сессии после восстановления backup.

Поиск дохода сейчас создаёт ссылки для поиска и непроверенный черновик по предоставленным фактам. Подключений к банкам, проверенных живых вакансий и отправки откликов нет.

## Стек

| Слой | Реализация |
| --- | --- |
| Интерфейс | TypeScript strict, React, Vite, CSS; общий responsive web для ПК/Android/iPhone |
| API и фоновые процессы | Python 3.12, FastAPI, Pydantic, SQLAlchemy, MCP SDK |
| Данные | PostgreSQL в облаке, SQLite для локальной разработки; Alembic migrations |
| Контракты | Pydantic → OpenAPI → generated TypeScript types |
| Запуск | Docker/Compose локально; один Render Free web + Free PostgreSQL для теста |
| Проверки | pytest, Vitest, TypeScript/build, contract drift; PostgreSQL, container smoke и Playwright в CI |

Есть manifest и публичная offline-страница через service worker; финансовые ответы не кэшируются. Push, native iOS/Android пакеты и проверка на настоящих телефонах ещё не выполнены. Обоснование языков: [STACK](docs/STACK.md).

## Запуск

[RUNNING](docs/RUNNING.md) — команды для Docker Compose и локальной разработки. [DEPLOYMENT](docs/DEPLOYMENT.md) — облачный запуск.

```bash
cp .env.example .env
# Укажите собственные MOZHNA_PASSWORD и POSTGRES_PASSWORD в .env.
docker compose up --build -d
```

После запуска на своём компьютере откройте `http://localhost:8000`. Это локальный адрес, не размещённая версия приложения. Compose хранит PostgreSQL в именованном volume.

## Карта проекта

| Папка | Содержание |
| --- | --- |
| [apps/web](apps/web/README.md) | Интерфейс и генерируемые API-типы |
| [services/backend](services/backend/README.md) | Money, API, MCP, jobs, providers, migrations, tests |
| [packages/schemas](packages/schemas/openapi.json) | OpenAPI contract |
| [docs](docs/README.md) | Продукт, архитектура, запуск, состояние и roadmap |
| [infra](infra/README.md) | Инструкции контейнера и Render |
| [scripts](scripts/README.md) | Проверка документации, генерация схемы, smoke |

Читайте [CONTRIBUTING](CONTRIBUTING.md) и [AGENTS](AGENTS.md). Lockfiles закреплены. Секретов и личных финансовых данных в репозитории нет. Лицензию распространения владелец пока не выбрал.
