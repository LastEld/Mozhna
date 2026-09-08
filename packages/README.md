# Общие контракты

[schemas/openapi.json](schemas/openapi.json) генерируется из FastAPI/Pydantic скриптом [export_openapi.py](../scripts/export_openapi.py). TypeScript-типы находятся в apps/web/src/api.generated.ts. Runtime CI проверяет drift.

Money остаётся внутренним Python-модулем; отдельного дублирующего npm Money Kernel нет.
