# Build context: workspace root (docker-compose sets context: ..)
FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_CACHE_DIR=/tmp/uv-cache \
    UV_PYTHON_DOWNLOADS=never

# Copy workspace manifest and lockfile first for layer caching
COPY pyproject.toml uv.lock .python-version ./

# Copy only the packages this service needs
COPY packages/beacon ./packages/beacon
COPY packages/agent-scout ./packages/agent-scout

# Install agent-scout (pulls beacon as a workspace dep)
RUN uv sync --frozen --no-dev --package agent-scout \
    && rm -rf /tmp/uv-cache

# State directory (override with STATE_DIR env var; mount a volume here)
VOLUME /var/lib/agentsentry/scout

CMD ["uv", "run", "--no-sync", "--package", "agent-scout", "agent-scout"]
