#!/usr/bin/env bash
# AgentSentry — Update Script
# Pulls latest code, syncs deps, runs migrations, rebuilds frontend, restarts services.
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/agentsentry}"
DB_USER="${DB_USER:-agentsentry}"
DB_PASS="${DB_PASS:-changeme}"
DB_NAME="${DB_NAME:-agentsentry}"

info()  { echo "[INFO]  $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

[[ "$EUID" -eq 0 ]] || error "Run as root: sudo $0"
[[ -d "$INSTALL_DIR/.git" ]] || error "No repository found at $INSTALL_DIR. Run install.sh first."

# ---------------------------------------------------------------------------
# STEP 1 — Pull latest code
# ---------------------------------------------------------------------------
info "Pulling latest code..."
git -C "$INSTALL_DIR" pull --ff-only

# ---------------------------------------------------------------------------
# STEP 2 — Sync Python dependencies
# ---------------------------------------------------------------------------
info "Syncing Python dependencies..."
cd "$INSTALL_DIR"
uv sync --frozen --no-dev

# ---------------------------------------------------------------------------
# STEP 3 — Rebuild frontend
# ---------------------------------------------------------------------------
info "Rebuilding dashboard..."
cd "$INSTALL_DIR/packages/dashboard"
pnpm install --frozen-lockfile
NEXT_TELEMETRY_DISABLED=1 pnpm build

# ---------------------------------------------------------------------------
# STEP 4 — Run database migrations
# ---------------------------------------------------------------------------
info "Running database migrations..."
cd "$INSTALL_DIR/packages/watchtower"
DATABASE_URL="postgresql+asyncpg://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME" \
  uv run --no-sync alembic upgrade head

# ---------------------------------------------------------------------------
# STEP 5 — Restart services
# ---------------------------------------------------------------------------
info "Restarting services..."
systemctl restart agentsentry-watchtower agentsentry-scout agentsentry-dashboard

info "Update complete. Services restarted."
systemctl status agentsentry-watchtower agentsentry-scout agentsentry-dashboard --no-pager -l
