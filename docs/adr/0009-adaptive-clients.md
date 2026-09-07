# Общий клиент на разных устройствах

Статус: DECIDED. Дата: 2026-09-07. Основание: поручение поддержать ПК/Android/iPhone и другие устройства; [CONTEXT](../CONTEXT.md).

## Решение

TypeScript/React/Vite PWA; responsive CSS и capability detection. Установка, push, камера и SSE — улучшения, базовые flows работают через браузер/file picker/polling. Capacitor выбран для будущей native-упаковки при нужной функции или публикации в магазинах.

Cloud state первичен, offline не подтверждает устаревшие финансовые решения. Финансовая логика не переносится на устройство. Один generated API client для PWA и будущей оболочки.

## Проверка

Viewport matrix, keyboard/accessibility, реальные iPhone/Safari и Android/Chrome, ПК, resume/reconnect. Browser engine tests в CI не заменяют проверку настоящего устройства. Native подпись/магазины пока не настроены.

Полный контракт: [CLIENTS](../CLIENTS.md).
