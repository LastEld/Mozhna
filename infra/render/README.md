# Render

Исполняемая конфигурация находится в корневом [render.yaml](../../render.yaml). API/web + worker + scheduler + PostgreSQL 17, Frankfurt; расходы показываются перед созданием. Auto deploy выключен. [Порядок развёртывания](../../docs/DEPLOYMENT.md).

Migrations выполняются pre-deploy web, background процессы ждут актуальный schema head. Фактический deployment ещё не выполнен.
