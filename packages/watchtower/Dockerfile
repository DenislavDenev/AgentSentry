# Build context: workspace root (docker-compose sets context: ..)
#
# Stage 1 — build the Vite SPA
FROM node:20-slim AS frontend
WORKDIR /app
COPY pnpm-workspace.yaml ./
COPY packages/dashboard-vite/package.json ./packages/dashboard-vite/
RUN corepack enable && corepack prepare pnpm@9 --activate
RUN pnpm install --frozen-lockfile --filter dashboard-vite
COPY packages/dashboard-vite ./packages/dashboard-vite
RUN pnpm --filter dashboard-vite build

# Stage 2 — Python runtime with embedded SPA
FROM python:3.12-slim AS runtime
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_CACHE_DIR=/tmp/uv-cache \
    UV_PYTHON_DOWNLOADS=never \
    DASHBOARD_DIR=/app/dashboard-static

COPY pyproject.toml uv.lock .python-version ./
COPY packages/watchtower ./packages/watchtower

RUN uv sync --frozen --no-dev --package watchtower \
    && rm -rf /tmp/uv-cache

# Copy the built SPA assets into the image so DASHBOARD_DIR is always valid
COPY --from=frontend /app/packages/dashboard-vite/dist /app/dashboard-static

EXPOSE 8000

# Migrations run at startup via the FastAPI lifespan (alembic upgrade head).
CMD ["uv", "run", "--no-sync", "--project", "packages/watchtower", "watchtower"]
