# Запуск MOZHNA alpha

Код рассчитан на Python 3.12 и Node 24, uv 0.11.33 и pnpm 11.19.0. Зависимости закреплены в lockfiles. Все команды ниже запускаются из корня репозитория, если не указано иное.

## Docker Compose на своём компьютере

Нужны Docker Engine/Desktop и Compose v2.

```bash
cp .env.example .env
```

Заполните `.env`: `MOZHNA_PASSWORD` — длинный пароль владельца, `POSTGRES_PASSWORD` — отдельный случайный пароль БД. Для Compose используйте URL-safe пароль БД (например, hex), поскольку он подставляется в DATABASE_URL. Остальные поля можно оставить пустыми; модели изначально выключены. Не отправляйте этот файл в GitHub.

```bash
docker compose up --build -d
docker compose ps
```

Откройте `http://localhost:8000` на этом компьютере и войдите паролем владельца. Compose поднимает PostgreSQL, один migration job, API, worker и scheduler. API привязан к loopback; этот режим не предназначен для публичного HTTP.

```bash
docker compose logs --tail=100 api worker scheduler
docker compose down
```

Обычный `down` оставляет volume БД. Не используйте `down -v`, если хотите сохранить данные. Для публикации на телефоне вне компьютера используйте HTTPS deployment, описанный в [DEPLOYMENT](DEPLOYMENT.md).

## Разработка без Docker

Нужны Python 3.12, uv, Node 24 и pnpm. Backend по умолчанию использует локальный SQLite-файл. Чтобы не хранить пароль в истории shell, сначала создайте локальный `.env` и загрузите необходимые значения своим менеджером окружения; автоматического чтения корневого `.env` Python-приложением нет.

Терминал API:

```bash
cd services/backend
uv sync --frozen
export MOZHNA_PASSWORD='replace-with-your-own-development-password'
export PUBLIC_ORIGIN=http://localhost:5173
uv run alembic upgrade head
uv run uvicorn mozhna.main:app --host 127.0.0.1 --port 8000 --reload
```

Замените показанное значение: это placeholder, не пароль развёрнутого приложения. Dev создаёт таблицы автоматически, но применение migrations нужно для проверки deployment path.

Терминал frontend:

```bash
cd apps/web
pnpm install --frozen-lockfile
pnpm dev
```

Откройте `http://localhost:5173`. Vite проксирует `/api` на backend. Для MCP используйте порт backend напрямую. SQLite DATABASE_URL и рабочая папка должны совпадать во всех backend-процессах.

Терминал worker:

```bash
cd services/backend
uv run python -m mozhna.worker
```

Терминал scheduler:

```bash
cd services/backend
uv run python -m mozhna.scheduler
```

Закрытие вкладки не останавливает задания, если эти процессы работают. Если остановлен компьютер с локальными процессами, локальное выполнение тоже остановится; постоянная работа требует облачного deployment.

## Проверка

```bash
python3 scripts/check_docs.py
cd services/backend
uv run pytest -q
uv run python ../../scripts/export_openapi.py
cd ../../apps/web
pnpm generate:api
pnpm test
pnpm build
```

PostgreSQL-тесты пропускаются без `TEST_DATABASE_URL` на отдельную тестовую БД. Тест реального dump/restore также требует `PG_CONTAINER_ID` контейнера PostgreSQL с утилитами и Docker CLI: он создаёт временную восстановленную БД и удаляет её после проверки. Не указывайте рабочую БД. Runtime CI предоставляет эти параметры, применяет migrations, запускает тесты конкурентного исполнения/auth/erase и собирает/запускает контейнер. `scripts/smoke_http.py` предназначен только для синтетического CI-контейнера.

### Браузерные сценарии

После установки backend и сборки frontend, из `apps/web`:

```bash
pnpm exec playwright install --with-deps chromium webkit
pnpm test:e2e
```

Playwright запускает отдельные API/worker на временной SQLite через `scripts/e2e_server.py`; все данные синтетические. Сценарии покрывают деньги, планы, наблюдения, фоновую job после закрытия вкладки, повторный CSV, потерю сети и конфликт двух версий. Проекты Pixel 7 и iPhone 13 используют эмуляцию viewport/touch в Chromium/WebKit, а не настоящие телефоны. GitHub Actions сохраняет отчёт, screenshots и failure traces в artifact `browser-evidence`. Результат нужно читать на соответствующем commit; наличие теста не означает его успешный запуск.

## Модели

На API и worker задайте одну и ту же конфигурацию:

| Переменная | Значение |
| --- | --- |
| ANTHROPIC_API_KEY / ANTHROPIC_MODEL | Собственный API-ключ и доступный model ID |
| GEMINI_API_KEY / GEMINI_MODEL | Собственный API-ключ и доступный model ID |
| MOZHNA_ALLOW_PAID_INFERENCE | `true` только после настройки billing limits |
| MOZHNA_DAILY_JOB_LIMIT | Общий лимит пользовательских jobs/24 часа, default 40 |

Перезапустите API и worker. Наличие ключей показывает «настроено», а не успешную проверку аккаунта. Подписки на пользовательские AI-приложения не заменяют эти API-ключи. В alpha нет monetary budget reservation или автоматического fallback. Сведения для черновика передаются выбранному провайдеру только по явному запуску задания пользователем.

## Remote MCP

На API задайте `MOZHNA_MCP_TOKEN` длиной минимум 32 случайных символа; в production обязательно HTTPS. При пустом значении endpoint отключён. Доступ: `/mcp/`, transport Streamable HTTP, заголовок `Authorization: Bearer <собственный токен>`.

Доступны `money_status`, `can_spend(amount_minor)`, `get_plans`, `get_jobs`. Все операции только читают или симулируют. Используйте AI-клиент, поддерживающий ручную настройку HTTP-заголовка; OAuth-подключение здесь не реализовано. Не вставляйте токен в URL, prompt или GitHub. Отзыв: очистить/сменить переменную и перезапустить API.

## Первый сценарий

Войдите → «Зараз» → внесите остаток и все неоплаченные обязательства → проверьте покупку. Можно явно загрузить синтетический пример. Затем создайте план, активируйте его, запишите наблюдение и запустите фоновое сравнение. На странице «Мій простір» проверьте результат, расписание и JSON-export.

Журнал не меняет snapshot: после оплаты вручную сверьте остаток и оставшиеся обязательства. Сценарная экономия не считается доходом.
