FROM node:24-bookworm-slim AS web
WORKDIR /src/apps/web
RUN npm install --global pnpm@11.19.0
COPY apps/web/package.json apps/web/pnpm-lock.yaml apps/web/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY apps/web/ ./
RUN pnpm build

FROM python:3.12-slim-bookworm AS runtime
COPY --from=ghcr.io/astral-sh/uv:0.11.33 /uv /usr/local/bin/uv
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app/services/backend
COPY services/backend/pyproject.toml services/backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY services/backend/ ./
COPY --from=web /src/apps/web/dist /app/apps/web/dist
RUN useradd --uid 10001 --no-create-home mozhna && mkdir /data && chown mozhna /data
ENV PATH="/app/services/backend/.venv/bin:$PATH" WEB_DIST_DIR=/app/apps/web/dist DATABASE_URL=sqlite:////data/mozhna.db
USER 10001
EXPOSE 8000
CMD ["uvicorn", "mozhna.main:app", "--host", "0.0.0.0", "--port", "8000"]
