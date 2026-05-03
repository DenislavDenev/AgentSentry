#!/usr/bin/env bash
# AgentSentry — Bare-Metal Installer
# Tested on: Ubuntu 24.04 LTS, Debian 12
set -euo pipefail

# ---------------------------------------------------------------------------
# CONFIGURATION — override via env vars or edit here
# ---------------------------------------------------------------------------
AGENT_DATA_DIR="${AGENT_DATA_DIR:-/opt/agent-data}"
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
  [[ "$EUID" -eq 0 ]] || error "Run this script as root (sudo $0)."
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
    error "Cannot detect OS — /etc/os-release not found."
  fi
}

# ---------------------------------------------------------------------------
# STEP 1 — System dependencies
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

  info "System dependencies installed."
}

# ---------------------------------------------------------------------------
# STEP 2 — uv
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
# STEP 3 — pnpm
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
# STEP 4 — Clone / update repository
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
# STEP 5 — Python workspace
# ---------------------------------------------------------------------------
install_python() {
  info "Installing Python workspace dependencies..."
  cd "$INSTALL_DIR"
  uv sync --frozen --no-dev
}

# ---------------------------------------------------------------------------
# STEP 6 — Frontend
# ---------------------------------------------------------------------------
install_frontend() {
  info "Building Next.js dashboard..."
  cd "$INSTALL_DIR/packages/dashboard"
  pnpm install --frozen-lockfile
  NEXT_TELEMETRY_DISABLED=1 pnpm build
}

# ---------------------------------------------------------------------------
# STEP 7 — PostgreSQL setup
# ---------------------------------------------------------------------------
setup_postgres() {
  info "Configuring PostgreSQL..."
  systemctl enable --now postgresql

  # Create role and database if they don't already exist
  sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" \
    | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"

  sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" \
    | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
}

# ---------------------------------------------------------------------------
# STEP 8 — Alembic migrations
# ---------------------------------------------------------------------------
run_migrations() {
  info "Running database migrations..."
  cd "$INSTALL_DIR/packages/watchtower"
  DATABASE_URL="postgresql+asyncpg://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME" \
    uv run --no-sync alembic upgrade head
}

# ---------------------------------------------------------------------------
# STEP 9 — Systemd units
# ---------------------------------------------------------------------------
write_systemd_units() {
  info "Writing systemd service units..."

  # Watchtower
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

  # AgentScout
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

  # Dashboard
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

  systemctl daemon-reload
  systemctl enable agentsentry-watchtower agentsentry-scout agentsentry-dashboard
  systemctl start  agentsentry-watchtower agentsentry-scout agentsentry-dashboard

  info "Services started. Check status with: systemctl status agentsentry-*"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  require_root
  detect_os

  info "=== AgentSentry Bare-Metal Installer ==="
  info "Install dir : $INSTALL_DIR"
  info "Agent data  : $AGENT_DATA_DIR"
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
  info "Dashboard : http://localhost:$DASHBOARD_PORT"
  info "API       : http://localhost:$WATCHTOWER_PORT"
  info ""
  info "Mount your agent log directory at $AGENT_DATA_DIR, then:"
  info "  systemctl restart agentsentry-scout"
}

main "$@"
