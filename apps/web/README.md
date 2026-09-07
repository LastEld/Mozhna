# Адаптивный web-клиент

Выбран TypeScript strict + React + Vite + CSS, PWA. Это единый клиент для браузеров ПК, Android, iPhone/iPad; native packaging позднее через Capacitor. Runtime ещё не создан.

Доменная арифметика выполняется Python backend. TypeScript API client генерируется из OpenAPI. Capability detection управляет camera/file picker, install, push и streaming; базовые сценарии работают без этих расширений.

Первый deployment отдаёт собранные assets под тем же origin, что API. Cloud job продолжается после закрытия вкладки; UI получает её по ID при возврате. Финансовые данные не кэшируются service worker по умолчанию.

Будущие компоненты: auth, money, plans, jobs/inbox, settings; responsive layout и i18n. Manifest, service worker, package.json и pnpm-lock.yaml добавляются вместе с реальной сборкой. См. [CLIENTS](../../docs/CLIENTS.md) и [STACK](../../docs/STACK.md).
