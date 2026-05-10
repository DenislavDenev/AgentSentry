#!/usr/bin/env bash
# AgentSentry — Update Script
# Pulls latest code, syncs deps, rebuilds Vite SPA, runs migrations, restarts service.
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/agentsentry}"

info()  { echo "[INFO]  $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

[[ "$EUID" -eq 0 ]] || error "Run as root: sudo $0"
[[ -d "$INSTALL_DIR/.git" ]] || error "No repository found at $INSTALL_DIR. Run install.sh first."

export PATH="$HOME/.local/bin:$PATH"

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
# STEP 3 — Rebuild Vite dashboard
# ---------------------------------------------------------------------------
info "Rebuilding Vite dashboard..."
cd "$INSTALL_DIR/packages/dashboard-vite"
pnpm install --frozen-lockfile
pnpm build

# ---------------------------------------------------------------------------
# STEP 4 — Restart service (migrations run automatically at startup)
# ---------------------------------------------------------------------------
info "Restarting service..."
systemctl restart agentsentry-watchtower

sleep 3
systemctl is-active agentsentry-watchtower || error "Service failed to restart. Check: journalctl -u agentsentry-watchtower -n 50"

info "Update complete."
systemctl status agentsentry-watchtower --no-pager -l
