#!/usr/bin/env bash
# Copyright (c) 2025 AgentSentry Contributors
# License: MIT  https://opensource.org/licenses/MIT
#
# AgentSentry — In-Container Installer
# Runs INSIDE the LXC created by ct/agentsentry.sh.
# Can also be run manually inside any Ubuntu 24.04 / Debian 12 LXC.
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
DB_NAME="${DB_NAME:-agentsentry}"
DB_USER="${DB_USER:-agentsentry}"
WATCHTOWER_PORT="${WATCHTOWER_PORT:-8000}"
DASHBOARD_PORT="${DASHBOARD_PORT:-3000}"
REPO="${REPO:-https://github.com/DenislavDenev/AgentSentry.git}"

# Generate password without triggering pipefail
if [[ -z "${DB_PASS:-}" ]]; then
  set +o pipefail
  DB_PASS=$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 16)
  set -o pipefail
fi

# ---------------------------------------------------------------------------
# STEP 1 — System packages
# ---------------------------------------------------------------------------
msg_info "Updating system packages"
silence apt-get update
silence apt-get install -y --no-install-recommends curl ca-certificates gnupg lsb-release
msg_ok "Base packages installed"

msg_info "Adding PostgreSQL 16 repository"
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
  | gpg --dearmor -o /usr/share/keyrings/postgresql.gpg 2>/dev/null
echo "deb [signed-by=/usr/share/keyrings/postgresql.gpg] \
  https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
  > /etc/apt/sources.list.d/pgdg.list
silence apt-get update
msg_ok "PostgreSQL repository added"

msg_info "Adding Node.js 22 repository"
curl -fsSL https://deb.nodesource.com/setup_22.x | silence bash -
msg_ok "Node.js repository added"

msg_info "Installing Python 3.12, Node.js 22, PostgreSQL 16"
silence apt-get install -y --no-install-recommends \
  python3.12 python3.12-venv python3-pip \
  nodejs \
  postgresql-16 postgresql-client-16 \
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
# STEP 3 — pnpm
# ---------------------------------------------------------------------------
msg_info "Installing pnpm"
silence corepack enable
silence corepack prepare pnpm@latest --activate
msg_ok "pnpm $(pnpm --version) installed"

# ---------------------------------------------------------------------------
# STEP 4 — Clone repository
# ---------------------------------------------------------------------------
msg_info "Cloning AgentSentry"
silence git clone "$REPO" "$INSTALL_DIR"
msg_ok "Repository cloned to $INSTALL_DIR"

# ---------------------------------------------------------------------------
# STEP 5 — Python workspace
# ---------------------------------------------------------------------------
msg_info "Installing Python dependencies"
cd "$INSTALL_DIR"
silence uv sync --frozen --no-dev
msg_ok "Python workspace ready"

# ---------------------------------------------------------------------------
# STEP 6 — Frontend build
# ---------------------------------------------------------------------------
msg_info "Installing dashboard dependencies"
cd "$INSTALL_DIR/packages/dashboard"
silence pnpm install --frozen-lockfile
msg_ok "Dashboard dependencies installed"

msg_info "Building dashboard (Next.js standalone)"
NEXT_TELEMETRY_DISABLED=1 silence pnpm build

# With pnpm workspaces, Next.js places server.js inside standalone/packages/dashboard/.
# Copy static assets alongside it so the server can resolve them at runtime.
STANDALONE="$INSTALL_DIR/packages/dashboard/.next/standalone/packages/dashboard"
mkdir -p "$STANDALONE/.next" "$STANDALONE/public"
cp -r "$INSTALL_DIR/packages/dashboard/.next/static"  "$STANDALONE/.next/static"
# Copy public/ only if it contains files (may be empty in a fresh checkout)
if [[ -d "$INSTALL_DIR/packages/dashboard/public" ]] && [[ -n "$(ls -A "$INSTALL_DIR/packages/dashboard/public" 2>/dev/null)" ]]; then
  cp -r "$INSTALL_DIR/packages/dashboard/public/." "$STANDALONE/public/"
fi
msg_ok "Dashboard built"

# ---------------------------------------------------------------------------
# STEP 7 — PostgreSQL
# ---------------------------------------------------------------------------
msg_info "Starting PostgreSQL"
silence systemctl enable --now postgresql

msg_info "Creating database user and database"
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" \
  | grep -q 1 \
  || silence sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" \
  | grep -q 1 \
  || silence sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

msg_ok "Database $DB_NAME created"

# ---------------------------------------------------------------------------
# STEP 8 — Alembic migrations
# ---------------------------------------------------------------------------
msg_info "Running database migrations"
cd "$INSTALL_DIR/packages/watchtower"
DATABASE_URL="postgresql+asyncpg://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME" \
  silence uv run --no-sync alembic upgrade head
msg_ok "Migrations complete"

# ---------------------------------------------------------------------------
# STEP 9 — Systemd units
# ---------------------------------------------------------------------------
msg_info "Writing systemd service units"

UV_BIN="$HOME/.local/bin/uv"

cat > /etc/systemd/system/agentsentry-watchtower.service <<EOF
[Unit]
Description=AgentSentry Watchtower API
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
Environment="DATABASE_URL=postgresql+asyncpg://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME"
ExecStart=$UV_BIN run --no-sync --package watchtower watchtower
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

mkdir -p "$STATE_DIR"
cat > /etc/systemd/system/agentsentry-scout.service <<EOF
[Unit]
Description=AgentSentry AgentScout Collector
After=network.target agentsentry-watchtower.service
Requires=agentsentry-watchtower.service

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
Environment="AGENT_DATA_DIR=$AGENT_DATA_DIR"
Environment="STATE_DIR=$STATE_DIR"
Environment="WATCHTOWER_URL=http://localhost:$WATCHTOWER_PORT"
ExecStart=$UV_BIN run --no-sync --package agent-scout agent-scout
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/agentsentry-dashboard.service <<EOF
[Unit]
Description=AgentSentry Dashboard
After=network.target agentsentry-watchtower.service

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR/packages/dashboard/.next/standalone/packages/dashboard
Environment="NODE_ENV=production"
Environment="NEXT_TELEMETRY_DISABLED=1"
Environment="PORT=$DASHBOARD_PORT"
Environment="HOSTNAME=0.0.0.0"
Environment="NEXT_PUBLIC_API_URL=http://localhost:$WATCHTOWER_PORT"
ExecStart=/usr/bin/node server.js
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

silence systemctl daemon-reload
silence systemctl enable agentsentry-watchtower agentsentry-scout agentsentry-dashboard
silence systemctl start agentsentry-watchtower agentsentry-scout agentsentry-dashboard
msg_ok "Services enabled and started"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
LAN_IP=$(hostname -I | awk '{print $1}')
echo ""
msg_ok "AgentSentry installation complete"
echo ""
echo -e "  ${GN}Dashboard${CL}  http://${LAN_IP}:$DASHBOARD_PORT"
echo -e "  ${GN}API      ${CL}  http://${LAN_IP}:$WATCHTOWER_PORT"
echo ""
echo -e "  ${YW}DB password stored in systemd unit. Retrieve with:${CL}"
echo -e "  systemctl cat agentsentry-watchtower | grep DATABASE_URL"
echo ""
