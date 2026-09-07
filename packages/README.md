# Общие контракты

Backend/Pydantic — канонические схемы; OpenAPI/JSON Schema и generated TypeScript client появляются здесь при первом API. Money Kernel остаётся внутри Python backend domain и не копируется в TypeScript.

Папки api-client и schemas создаются при генерации, когда существует проверенный source schema. CI проверяет drift. Отдельный package для каждой возможности не нужен.

Общая UI-логика остаётся apps/web и повторно используется Capacitor; device-specific plugin изолируется только по реальной необходимости. См. [STACK](../docs/STACK.md).
