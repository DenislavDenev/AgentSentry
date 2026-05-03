# Build context: workspace root (docker-compose sets context: ..)
# ---- builder ----------------------------------------------------------------
FROM node:22-alpine AS builder
WORKDIR /app

RUN corepack enable && corepack prepare pnpm@latest --activate

# Copy workspace manifests for pnpm to resolve the workspace
COPY pnpm-workspace.yaml pnpm-lock.yaml ./
# pnpm needs a root package.json even if empty
COPY package.json ./
COPY packages/dashboard ./packages/dashboard

# Install deps for dashboard only
RUN pnpm install --frozen-lockfile --filter dashboard

# Build (telemetry disabled at build time)
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm --filter dashboard build

# ---- runtime ----------------------------------------------------------------
FROM node:22-alpine AS runtime
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Next.js standalone output is self-contained
COPY --from=builder /app/packages/dashboard/.next/standalone/ ./
# Static assets and public dir must be added alongside the standalone server
COPY --from=builder /app/packages/dashboard/.next/static/ ./.next/static/
COPY --from=builder /app/packages/dashboard/public/ ./public/

EXPOSE 3000

CMD ["node", "server.js"]
