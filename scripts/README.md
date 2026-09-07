# Скрипты

`python3 scripts/check_docs.py` — проверка обязательных файлов, относительных ссылок на файлы в Markdown и JSON fixtures. Используется локально и в GitHub Actions, только Python standard library.

Проверка не обходит внешние сайты, не проверяет Markdown anchors и не исполняет денежный расчёт. Продуктовые тесты появятся вместе с runtime.
