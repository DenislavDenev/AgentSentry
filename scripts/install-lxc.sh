#!/usr/bin/env bash
# AgentSentry — Proxmox LXC Installer
# Designed for Proxmox VE 8.x with an unprivileged LXC running Ubuntu 24.04 or Debian 12.
#
# PRE-REQUISITE (run on Proxmox HOST before executing this script inside the LXC):
#   The agent log directory from your AI-agent machine must be accessible inside
#   the LXC. Three options:
#
#   A) NFS — mount the share on the Proxmox host, then bind-mount into the LXC:
#        # On Proxmox host:
#        mount -t nfs 192.168.1.x:/export/agent-logs /mnt/agent-logs
#        # In /etc/pve/lxc/<CTID>.conf:
#        mp0: /mnt/agent-logs,mp=/data/agent-logs,ro=1
#
#   B) CIFS/SMB:
#        mount -t cifs //192.168.1.x/agent-logs /mnt/agent-logs \
#          -o ro,credentials=/etc/cifs-credentials,uid=0
#        # Then same mp0 line as above.
#
#   C) Local bind-mount (agent runs on the Proxmox host itself):
#        # In /etc/pve/lxc/<CTID>.conf:
#        mp0: /home/user/.claude,mp=/data/agent-logs,ro=1
#
set -euo pipefail

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
AGENT_DATA_DIR="${AGENT_DATA_DIR:-/data/agent-logs}"
INSTALL_DIR="${INSTALL_DIR:-/opt/agentsentry}"
STATE_DIR="${STATE_DIR:-/var/lib/agentsentry/scout}"
DB_NAME="${DB_NAME:-agentsentry}"
DB_USER="${DB_USER:-agentsentry}"
DB_PASS="${DB_PASS:-changeme}"
REPO="${REPO:-https://github.com/DenislavDenev/AgentSentry.git}"
WATCHTOWER_PORT="${WATCHTOWER_PORT:-8000}"
DASHBOARD_PORT="${DASHBOARD_PORT:-3000}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()  { echo "[INFO]  $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

require_root() {
  [[ "$EUID" -eq 0 ]] || error "Run this script as root inside the LXC."
}

detect_os() {
  if [[ -f /etc/os-release ]]; then
    # shellcheck source=/dev/null
    . /etc/os-release
    case "$ID" in
      ubuntu|debian) return 0 ;;
      *) error "Unsupported distro: $ID. Supported: Ubuntu 24.04, Debian 12." ;;
    esac
  else
    error "Cannot detect OS."
  fi
}

# ---------------------------------------------------------------------------
# STEP 1 — Validate bind-mount
# ---------------------------------------------------------------------------
validate_mount() {
  info "Checking agent data mount at $AGENT_DATA_DIR..."
  if [[ ! -d "$AGENT_DATA_DIR" ]]; then
    error "$AGENT_DATA_DIR does not exist. Set up the Proxmox bind-mount first (see script header)."
  fi
  if [[ ! -r "$AGENT_DATA_DIR" ]]; then
    error "$AGENT_DATA_DIR exists but is not readable. Check LXC bind-mount permissions."
  fi
  # Check that there's at least a projects/ subdirectory or it's empty (new install)
  if [[ -d "$AGENT_DATA_DIR/projects" ]]; then
    info "Found projects/ directory — mount looks correct."
  else
    info "Warning: no projects/ subdirectory found in $AGENT_DATA_DIR."
    info "AgentScout will watch this path once Claude Code creates session files."
  fi
}

# ---------------------------------------------------------------------------
# STEP 2 — System dependencies
# ---------------------------------------------------------------------------
install_system_deps() {
  info "Installing system dependencies..."
  apt-get update -qq

  # PostgreSQL 16
  if ! command -v psql &>/dev/null; then
    info "Adding PostgreSQL 16 apt repository..."
    apt-get install -y --no-install-recommends curl ca-certificates gnupg lsb-release
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
      | gpg --dearmor -o /usr/share/keyrings/postgresql.gpg
    echo "deb [signed-by=/usr/share/keyrings/postgresql.gpg] \
      https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
      > /etc/apt/sources.list.d/pgdg.list
    apt-get update -qq
  fi

  # Node.js 22 via NodeSource
  if ! command -v node &>/dev/null || [[ "$(node --version | cut -d. -f1)" != "v22" ]]; then
    info "Adding Node.js 22 repository..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  fi

  apt-get install -y --no-install-recommends \
    python3.12 python3.12-venv python3-pip \
    nodejs \
    postgresql-16 postgresql-client-16 \
    git curl ca-certificates
}

# ---------------------------------------------------------------------------
# STEP 3 — uv
# ---------------------------------------------------------------------------
install_uv() {
  if ! command -v uv &>/dev/null; then
    info "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
  else
    info "uv already installed: $(uv --version)"
  fi
}

# ---------------------------------------------------------------------------
# STEP 4 — pnpm
# ---------------------------------------------------------------------------
install_pnpm() {
  if ! command -v pnpm &>/dev/null; then
    info "Installing pnpm via corepack..."
    corepack enable
    corepack prepare pnpm@latest --activate
  else
    info "pnpm already installed: $(pnpm --version)"
  fi
}

# ---------------------------------------------------------------------------
# STEP 5 — Clone / update repository
# ---------------------------------------------------------------------------
install_repo() {
  if [[ -d "$INSTALL_DIR/.git" ]]; then
    info "Repository already exists at $INSTALL_DIR — pulling latest..."
    git -C "$INSTALL_DIR" pull --ff-only
  else
    info "Cloning AgentSentry to $INSTALL_DIR..."
    git clone "$REPO" "$INSTALL_DIR"
  fi
}

# ---------------------------------------------------------------------------
# STEP 6 — Python workspace
# ---------------------------------------------------------------------------
install_python() {
  info "Installing Python workspace dependencies..."
  cd "$INSTALL_DIR"
  uv sync --frozen --no-dev
}

# ---------------------------------------------------------------------------
# STEP 7 — Frontend
# ---------------------------------------------------------------------------
install_frontend() {
  info "Building Next.js dashboard..."
  cd "$INSTALL_DIR/packages/dashboard"
  pnpm install --frozen-lockfile
  NEXT_TELEMETRY_DISABLED=1 pnpm build
}

# ---------------------------------------------------------------------------
# STEP 8 — PostgreSQL setup
# ---------------------------------------------------------------------------
setup_postgres() {
  info "Configuring PostgreSQL..."
  systemctl enable --now postgresql

  sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" \
    | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"

  sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" \
    | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
}

# ---------------------------------------------------------------------------
# STEP 9 — Alembic migrations
# ---------------------------------------------------------------------------
run_migrations() {
  info "Running database migrations..."
  cd "$INSTALL_DIR/packages/watchtower"
  DATABASE_URL="postgresql+asyncpg://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME" \
    uv run --no-sync alembic upgrade head
}

# ---------------------------------------------------------------------------
# STEP 10 — Systemd units
# ---------------------------------------------------------------------------
write_systemd_units() {
  info "Writing systemd service units..."

  cat > /etc/systemd/system/agentsentry-watchtower.service <<EOF
[Unit]
Description=AgentSentry Watchtower API
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
Environment="DATABASE_URL=postgresql+asyncpg://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME"
ExecStart=$HOME/.local/bin/uv run --no-sync --package watchtower watchtower
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
ExecStart=$HOME/.local/bin/uv run --no-sync --package agent-scout agent-scout
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
WorkingDirectory=$INSTALL_DIR/packages/dashboard/.next/standalone
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

  systemctl daemon-reload
  systemctl enable agentsentry-watchtower agentsentry-scout agentsentry-dashboard
  systemctl start  agentsentry-watchtower agentsentry-scout agentsentry-dashboard

  info "Services started."
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  require_root
  detect_os
  validate_mount

  info "=== AgentSentry Proxmox LXC Installer ==="
  info "Install dir : $INSTALL_DIR"
  info "Agent data  : $AGENT_DATA_DIR (bind-mounted read-only)"
  info "Database    : $DB_NAME @ localhost"

  install_system_deps
  install_uv
  install_pnpm
  install_repo
  install_python
  install_frontend
  setup_postgres
  run_migrations
  write_systemd_units

  echo ""
  info "=== Installation complete ==="
  info "Dashboard : http://<LXC-IP>:$DASHBOARD_PORT"
  info "API       : http://<LXC-IP>:$WATCHTOWER_PORT"
}

main "$@"
