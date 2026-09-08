# Адаптивный web-клиент

TypeScript strict, React, Vite и CSS. `pnpm install --frozen-lockfile`, `pnpm dev`; backend запустить отдельно по [RUNNING](../../docs/RUNNING.md). Production: `pnpm build`, затем backend обслуживает dist под тем же origin.

Пять экранов: деньги, планы, журнал/CSV, направления дохода, настройки/фоновые задачи. Украинский интерфейс, sidebar на ПК и нижняя навигация на телефоне. Суммы для финансовых решений и наблюдений считает сервер. API-типы генерируются `pnpm generate:api` из OpenAPI; `src/api.generated.ts` не редактируется вручную.

Polling и focus/reconnect обновляют состояние. Открытая форма сохраняет исходную версию snapshot: чужое обновление приводит к конфликту вместо тихой перезаписи. Суммы разбираются и форматируются точно в целых cents. Есть manifest и service worker только для публичной offline-страницы; финансовый cache, offline writes, push, native пакеты отсутствуют. Real-device QA ещё не выполнена. Изолированный статический frontend без работающего API не является приложением.

`pnpm test` проверяет денежный ввод и форматирование. `pnpm test:e2e` запускает Playwright против отдельного синтетического API/worker: Desktop Chrome, Pixel 7/Chromium и iPhone 13/WebKit. Требуются собранный frontend, установленный backend и браузеры Playwright; команды — в [RUNNING](../../docs/RUNNING.md). Offline reload WebKit воспроизводимо не проходит и отмечен ожидаемым сбоем `WEBKIT-OFFLINE-01`; остальные сценарии проверяются отдельно. Это не доказательство готовности iPhone offline.

[Состояние alpha](../../docs/IMPLEMENTATION.md), [стратегия устройств](../../docs/CLIENTS.md).
