#!/usr/bin/env bash
# AgentSentry — Bare-Metal Installer
# Tested on: Ubuntu 24.04 LTS, Debian 12
#
# One service. One SQLite file. No Postgres. No Node runtime in production.
#
# Usage:
#   sudo AGENT_DATA_DIR=/path/to/.claude ./scripts/install.sh
set -euo pipefail

# ---------------------------------------------------------------------------
# CONFIGURATION — override via env vars
# ---------------------------------------------------------------------------
AGENT_DATA_DIR="${AGENT_DATA_DIR:-/data/agent-logs}"
INSTALL_DIR="${INSTALL_DIR:-/opt/agentsentry}"
STATE_DIR="${STATE_DIR:-/var/lib/agentsentry/scout}"
PORT="${PORT:-8000}"
REPO="${REPO:-https://github.com/DenislavDenev/AgentSentry.git}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()  { echo "[INFO]  $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

require_root() {
  [[ "$EUID" -eq 0 ]] || error "Run this script as root (sudo $0)."
}

detect_os() {
  [[ -f /etc/os-release ]] || error "Cannot detect OS — /etc/os-release not found."
  # shellcheck source=/dev/null
  . /etc/os-release
  case "$ID" in
    ubuntu|debian) ;;
    *) error "Unsupported distro: $ID. Supported: Ubuntu 24.04, Debian 12." ;;
  esac
}

# ---------------------------------------------------------------------------
# STEP 1 — System dependencies
# ---------------------------------------------------------------------------
install_system_deps() {
  info "Installing system dependencies..."
  apt-get update -qq

  # Node.js 20 LTS — build-time only, not needed at runtime
  if ! command -v node &>/dev/null || [[ "$(node --version | cut -d. -f1)" != "v20" ]]; then
    info "Adding Node.js 20 repository..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  fi

  # python3/python3-venv are distro-agnostic (Debian 12 ships 3.11, Ubuntu
  # 24.04 ships 3.12). uv manages the actual Python 3.12 runtime itself via
  # its bundled CPython distribution — no version-pinned apt package needed.
  apt-get install -y --no-install-recommends \
    python3 python3-venv \
    nodejs \
    git curl ca-certificates

  info "System dependencies installed."
}

# ---------------------------------------------------------------------------
# STEP 2 — uv
# ---------------------------------------------------------------------------
install_uv() {
  if ! command -v uv &>/dev/null && [[ ! -x "$HOME/.local/bin/uv" ]]; then
    info "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
  fi
  export PATH="$HOME/.local/bin:$PATH"
  info "uv $(uv --version) ready"
}

# ---------------------------------------------------------------------------
# STEP 3 — pnpm (pinned to 9)
# ---------------------------------------------------------------------------
install_pnpm() {
  if ! command -v pnpm &>/dev/null; then
    info "Installing pnpm 9 via corepack..."
    corepack enable
    corepack prepare pnpm@9 --activate
  fi
  info "pnpm $(pnpm --version) ready"
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
# STEP 5 — Python workspace (watchtower only)
# ---------------------------------------------------------------------------
install_python() {
  info "Installing Python dependencies..."
  cd "$INSTALL_DIR"
  uv sync --frozen --no-dev
  info "Python workspace ready"
}

# ---------------------------------------------------------------------------
# STEP 6 — Vite SPA build
# ---------------------------------------------------------------------------
install_frontend() {
  info "Building Vite dashboard..."
  cd "$INSTALL_DIR/packages/dashboard-vite"
  pnpm install --frozen-lockfile
  pnpm build
  info "Dashboard built at $INSTALL_DIR/packages/dashboard-vite/dist"
}

# ---------------------------------------------------------------------------
# STEP 7 — Data directories and SQLite location
# ---------------------------------------------------------------------------
create_dirs() {
  mkdir -p "$STATE_DIR"
  mkdir -p /var/lib/agentsentry
}

# ---------------------------------------------------------------------------
# STEP 8 — Systemd unit (single service)
# ---------------------------------------------------------------------------
write_systemd_unit() {
  info "Writing systemd service unit..."

  UV_BIN="$(command -v uv 2>/dev/null || echo "$HOME/.local/bin/uv")"

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

  systemctl daemon-reload
  systemctl enable agentsentry-watchtower
  systemctl restart agentsentry-watchtower

  info "Service started."
}

# ---------------------------------------------------------------------------
# STEP 9 — Smoke test
# ---------------------------------------------------------------------------
smoke_test() {
  info "Waiting for service to become ready (up to 30 s)..."
  local deadline=$((SECONDS + 30)) code
  until [[ $SECONDS -ge $deadline ]]; do
    code=$(curl -sf -o /dev/null -w "%{http_code}" "http://localhost:$PORT/api/stats/overview" 2>/dev/null || echo "000")
    if [[ "$code" == "200" ]]; then break; fi
    sleep 3
  done

  if [[ "$code" != "200" ]]; then
    error "Smoke test FAILED after 30 s: /api/stats/overview returned $code. Check: journalctl -u agentsentry-watchtower -n 50"
  fi

  local html_code
  html_code=$(curl -sf -o /dev/null -w "%{http_code}" "http://localhost:$PORT/" 2>/dev/null || echo "000")
  if [[ "$html_code" != "200" ]]; then
    error "Smoke test FAILED: GET / returned $html_code (dashboard not served)"
  fi

  info "Smoke test passed (/ -> $html_code, /api/stats/overview -> $code)"
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
  info "Port        : $PORT"

  install_system_deps
  install_uv
  install_pnpm
  install_repo
  install_python
  install_frontend
  create_dirs
  write_systemd_unit
  smoke_test

  echo ""
  info "=== Installation complete ==="
  info "Dashboard : http://$(hostname -I | awk '{print $1}'):$PORT"
  echo ""
  info "Logs : journalctl -u agentsentry-watchtower -f"
}

main "$@"
