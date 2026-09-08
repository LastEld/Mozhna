# Адаптивный web-клиент

TypeScript strict, React, Vite и CSS. `pnpm install --frozen-lockfile`, `pnpm dev`; backend запустить отдельно по [RUNNING](../../docs/RUNNING.md). Production: `pnpm build`, затем backend обслуживает dist под тем же origin.

Пять экранов: деньги, планы, журнал/CSV, направления дохода, настройки/фоновые задачи. Украинский интерфейс, sidebar на ПК и нижняя навигация на телефоне. Суммы для финансовых решений и наблюдений считает сервер. API-типы генерируются `pnpm generate:api` из OpenAPI; `src/api.generated.ts` не редактируется вручную.

Polling и focus/reconnect обновляют состояние. Версии защищают изменения с разных устройств. Есть manifest; нет service worker, offline writes, push, native пакетов и заявленной real-device QA. Изолированный статический frontend без работающего API не является приложением.

[Состояние alpha](../../docs/IMPLEMENTATION.md), [стратегия устройств](../../docs/CLIENTS.md).
