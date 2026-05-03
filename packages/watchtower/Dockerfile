# Build context: workspace root (docker-compose sets context: ..)
FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_CACHE_DIR=/tmp/uv-cache \
    UV_PYTHON_DOWNLOADS=never

COPY pyproject.toml uv.lock .python-version ./
COPY packages/watchtower ./packages/watchtower

RUN uv sync --frozen --no-dev --package watchtower \
    && rm -rf /tmp/uv-cache

EXPOSE 8000

# Run Alembic migrations then start the server
CMD ["sh", "-c", \
    "cd /app/packages/watchtower && \
     uv run --no-sync alembic upgrade head && \
     cd /app && \
     exec uv run --no-sync --package watchtower watchtower"]
