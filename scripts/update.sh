#!/usr/bin/env bash
# AgentSentry — Update Script
# Handles: code pull, dependency sync, migrations, service restarts.
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/agentsentry}"

# ---------------------------------------------------------------------------
# [STEP 1] Pull latest code
# ---------------------------------------------------------------------------
# TODO: git -C "$INSTALL_DIR" pull --ff-only

# ---------------------------------------------------------------------------
# [STEP 2] Sync Python dependencies
# ---------------------------------------------------------------------------
# TODO: cd "$INSTALL_DIR" && uv sync

# ---------------------------------------------------------------------------
# [STEP 3] Rebuild frontend
# ---------------------------------------------------------------------------
# TODO: cd "$INSTALL_DIR/packages/dashboard" && pnpm install && pnpm build

# ---------------------------------------------------------------------------
# [STEP 4] Run database migrations
# ---------------------------------------------------------------------------
# TODO: cd "$INSTALL_DIR" && uv run alembic upgrade head

# ---------------------------------------------------------------------------
# [STEP 5] Restart services
# ---------------------------------------------------------------------------
# TODO: systemctl restart agentsentry-scout agentsentry-beacon agentsentry-watchtower agentsentry-dashboard

echo "AgentSentry update stub complete. Implement steps above for Phase 6."
