#!/usr/bin/env bash
# Copyright (c) 2025 AgentSentry Contributors
# License: MIT  https://opensource.org/licenses/MIT
#
# AgentSentry — In-Container Installer
# Runs INSIDE the LXC created by ct/agentsentry.sh.
# Can also be run manually inside any Ubuntu 24.04 / Debian 12 LXC.
#
# One service. One SQLite file. No Postgres. No Node runtime in production.
set -euo pipefail

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
YW=$(echo "\033[33m")
GN=$(echo "\033[1;92m")
RD=$(echo "\033[01;31m")
BL=$(echo "\033[36m")
CL=$(echo "\033[m")
CM="${GN}✓${CL}"
CROSS="${RD}✗${CL}"
INFO="${BL}ℹ${CL}"

msg_info()  { echo -e " ${INFO} ${YW}$*${CL}"; }
msg_ok()    { echo -e " ${CM} ${GN}$*${CL}"; }
msg_error() { echo -e " ${CROSS} ${RD}$*${CL}" >&2; exit 1; }

# Suppress verbose output from commands
silence() { "$@" &>/dev/null; }

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
INSTALL_DIR="${INSTALL_DIR:-/opt/agentsentry}"
STATE_DIR="${STATE_DIR:-/var/lib/agentsentry/scout}"
AGENT_DATA_DIR="${AGENT_DATA_DIR:-/data/agent-logs}"
PORT="${PORT:-8000}"
REPO="${REPO:-https://github.com/DenislavDenev/AgentSentry.git}"

# ---------------------------------------------------------------------------
# STEP 1 — System packages
# ---------------------------------------------------------------------------
msg_info "Updating system packages"
silence apt-get update
silence apt-get install -y --no-install-recommends curl ca-certificates gnupg lsb-release
msg_ok "Base packages installed"

# Node.js 20 LTS — build-time only, not needed at runtime
msg_info "Adding Node.js 20 repository"
curl -fsSL https://deb.nodesource.com/setup_20.x | silence bash -
msg_ok "Node.js repository added"

msg_info "Installing Python 3.12 and Node.js 20"
silence apt-get install -y --no-install-recommends \
  python3.12 python3.12-venv python3-pip \
  nodejs \
  git
msg_ok "System packages installed"

# ---------------------------------------------------------------------------
# STEP 2 — uv
# ---------------------------------------------------------------------------
msg_info "Installing uv"
curl -LsSf https://astral.sh/uv/install.sh | silence sh
export PATH="$HOME/.local/bin:$PATH"
msg_ok "uv $(uv --version) installed"

# ---------------------------------------------------------------------------
# STEP 3 — pnpm (pinned to 9)
# ---------------------------------------------------------------------------
msg_info "Installing pnpm 9"
silence corepack enable
silence corepack prepare pnpm@9 --activate
msg_ok "pnpm $(pnpm --version) installed"

# ---------------------------------------------------------------------------
# STEP 4 — Clone repository
# ---------------------------------------------------------------------------
msg_info "Cloning AgentSentry"
silence git clone "$REPO" "$INSTALL_DIR"
msg_ok "Repository cloned to $INSTALL_DIR"

# ---------------------------------------------------------------------------
# STEP 5 — Python workspace (watchtower only)
# ---------------------------------------------------------------------------
msg_info "Installing Python dependencies"
cd "$INSTALL_DIR"
silence uv sync --frozen --no-dev
msg_ok "Python workspace ready"

# ---------------------------------------------------------------------------
# STEP 6 — Vite SPA build
# ---------------------------------------------------------------------------
msg_info "Installing dashboard dependencies"
cd "$INSTALL_DIR/packages/dashboard-vite"
silence pnpm install --frozen-lockfile
msg_ok "Dashboard dependencies installed"

msg_info "Building Vite dashboard"
silence pnpm build
msg_ok "Dashboard built at $INSTALL_DIR/packages/dashboard-vite/dist"

# ---------------------------------------------------------------------------
# STEP 7 — Data directories and SQLite location
# ---------------------------------------------------------------------------
msg_info "Creating data directories"
mkdir -p "$STATE_DIR"
mkdir -p /var/lib/agentsentry
msg_ok "Directories ready"

# ---------------------------------------------------------------------------
# STEP 8 — Systemd unit (single service)
# ---------------------------------------------------------------------------
msg_info "Writing systemd service unit"

UV_BIN="$HOME/.local/bin/uv"

cat > /etc/systemd/system/agentsentry-watchtower.service <<EOF
[Unit]
Description=AgentSentry Watchtower
After=network.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
Environment="DATABASE_URL=sqlite+aiosqlite:////var/lib/agentsentry/agentsentry.db"
Environment="AGENT_DATA_DIR=$AGENT_DATA_DIR"
Environment="STATE_DIR=$STATE_DIR"
Environment="DASHBOARD_DIR=$INSTALL_DIR/packages/dashboard-vite/dist"
Environment="PORT=$PORT"
ExecStart=$UV_BIN run --no-sync --project packages/watchtower watchtower
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

silence systemctl daemon-reload
silence systemctl enable agentsentry-watchtower
silence systemctl start agentsentry-watchtower
msg_ok "Service enabled and started"

# ---------------------------------------------------------------------------
# STEP 9 — Smoke test
# ---------------------------------------------------------------------------
msg_info "Running smoke test"
sleep 4
HTML_CODE=$(curl -sf -o /dev/null -w "%{http_code}" "http://localhost:$PORT/" || echo "000")
JSON_CODE=$(curl -sf -o /dev/null -w "%{http_code}" "http://localhost:$PORT/api/stats/overview" || echo "000")

if [[ "$HTML_CODE" != "200" ]]; then
  msg_error "Smoke test FAILED: GET / returned $HTML_CODE. Check: journalctl -u agentsentry-watchtower -n 50"
fi
if [[ "$JSON_CODE" != "200" ]]; then
  msg_error "Smoke test FAILED: GET /api/stats/overview returned $JSON_CODE"
fi
msg_ok "Smoke test passed"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
LAN_IP=$(hostname -I | awk '{print $1}')
echo ""
msg_ok "AgentSentry installation complete"
echo ""
echo -e "  ${GN}Dashboard${CL}  http://${LAN_IP}:$PORT"
echo ""
echo -e "  ${YW}Logs:${CL}  journalctl -u agentsentry-watchtower -f"
echo ""
