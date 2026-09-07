# Первый облачный backlog

Работы ещё не выполнены. Это задачи для разработки, не автоматически созданные GitHub Issues. Стек и облачная форма выбраны: не начинать заново обсуждение языков.

| ID | Работа | Done | Зависимости |
| --- | --- | --- | --- |
| CLOUD-01 | Python/FastAPI и React/Vite skeleton, lockfiles, image | Реальные команды, build, CI и runtime versions зафиксированы; web/API на одном origin | Нет |
| AUTH-01 | Web login, workspace и MCP identity prerequisites | Проверен OIDC provider, cookie/CSRF, owner isolation; выбран совместимый MCP authorization server | CLOUD-01 |
| JOB-01 | PostgreSQL jobs/outbox, worker | Job атомарна с command; lease/fencing, restart, status и cancel проверены | CLOUD-01, AUTH-01 |
| SCHED-01 | Cloud scheduler | schedule_id + due_at не дублируются; timezone/DST/missed-run правило проверено | JOB-01 |
| DEPLOY-01 | Staging на выбранной topology | API/worker/scheduler/DB доступны, secrets раздельны, health/restore smoke; создание ресурсов после готовой конфигурации и бюджета | CLOUD-01, AUTH-01, JOB-01 |
| MONEY-00 | Завершить money policy ADR | Горизонт/freshness/living budget зафиксированы до реализации формулы | Нет; вопрос policy остаётся открытым |
| MONEY-01 | Чистый domain Money | Integer minor units, currency, UNKNOWN, инварианты и replay | MONEY-00 |
| MONEY-02 | Cloud snapshots и версии | Перезапуск сохраняет данные, idempotent write, optimistic conflict | AUTH-01, MONEY-01 |
| UI-01 | Responsive money path | 320–1440 px, touch/keyboard, manual input → decision, cloud resume | MONEY-02 |
| TRUST-01 | Export/delete и private state | Нет утечки чужих данных, cache очищается, restore не оживляет права | MONEY-02 |
| MODEL-01 | ModelProvider + Anthropic adapter | Typed request/result, capabilities, usage budget, timeout/refusal/invalid output | JOB-01 |
| MODEL-02 | Gemini adapter + общий contract suite | Один snapshot через два реальных providers при разрешённом test budget; fake-only не закрывает задачу | MODEL-01 |
| MCP-01 | Remote Streamable HTTP | OAuth/scopes, get_context/simulate/get_job/cancel_job через real client | AUTH-01, JOB-01, MONEY-02 |
| DEVICE-01 | Real-device alpha QA | iPhone/Safari, Android/Chrome и ПК: login, rotation, keyboard, reconnect, resume | UI-01, DEPLOY-01 |
| EVAL-01 | Baseline и польза ручного пути | Протокол до наблюдений, результаты с ограничениями; стоимость облака видна | UI-01 |

Следом: PLAN-01 — облачный цикл привычки; INGEST-01 — CSV/чеки и каноническая сверка; BANK-01 — один read-only provider после source gate; EARN-01 — профиль/поиск/drafts по продуктовому порядку; ACTION-01 — confirmed submit; NATIVE-01 — Capacitor только при конкретной потребности.

Cloud scaffolding не должно блокировать реализацию чистого Money Kernel: эти части можно выполнять независимо, если поручена такая работа. Связи задач обозначают зависимости поведения, а не требование заводить отдельный сервис на каждую строку.

Для Claude Code: прочитать [AGENTS](../AGENTS.md), взять первый порученный незавершённый срез, довести до запуска и проверки. Новая просьба выбрать облачную архитектуру уже разрешила обычный технический выбор; дополнительных approvals на языки не нужно. Неизвестные credentials и результаты тестов не придумывать.
