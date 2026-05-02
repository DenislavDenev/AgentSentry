#!/usr/bin/env bash
# AgentSentry — Proxmox LXC Installer
# Designed for Proxmox VE 8.x with an unprivileged LXC running Ubuntu 24.04 or Debian 12.
set -euo pipefail

# ---------------------------------------------------------------------------
# CONFIGURATION — edit these before running
# ---------------------------------------------------------------------------
AGENT_DATA_DIR="${AGENT_DATA_DIR:-/data/agent-logs}"   # Read-only bind-mount target inside the LXC
INSTALL_DIR="${INSTALL_DIR:-/opt/agentsentry}"
DB_NAME="${DB_NAME:-agentsentry}"
DB_USER="${DB_USER:-agentsentry}"
DB_PASS="${DB_PASS:-changeme}"                          # Change before production use

# ---------------------------------------------------------------------------
# [STEP 1] Bind-mount setup (run on Proxmox HOST, not inside LXC)
# ---------------------------------------------------------------------------
# The agent log directory lives on the machine running the AI agent (e.g., your
# workstation). You must expose it to this LXC via one of:
#   a) NFS share: mount the export at $AGENT_DATA_DIR before starting the LXC
#   b) CIFS/SMB share: mount with read-only credentials
#   c) Proxmox bind-mount: add to /etc/pve/lxc/<CTID>.conf:
#        mp0: /mnt/host/agent-logs,mp=/data/agent-logs,ro=1
#
# The application will NEVER write to this path. AgentScout opens files read-only.
# TODO: Validate $AGENT_DATA_DIR is mounted and accessible before proceeding.

# ---------------------------------------------------------------------------
# [STEP 2] System dependencies (inside LXC)
# ---------------------------------------------------------------------------
# TODO: apt-get install -y python3.12 python3.12-venv nodejs npm postgresql-16

# ---------------------------------------------------------------------------
# [STEP 3] Install uv (inside LXC)
# ---------------------------------------------------------------------------
# TODO: curl -LsSf https://astral.sh/uv/install.sh | sh

# ---------------------------------------------------------------------------
# [STEP 4] Install pnpm (inside LXC)
# ---------------------------------------------------------------------------
# TODO: npm install -g pnpm

# ---------------------------------------------------------------------------
# [STEP 5] Clone / copy application (inside LXC)
# ---------------------------------------------------------------------------
# TODO: git clone https://github.com/<org>/AgentSentry "$INSTALL_DIR"

# ---------------------------------------------------------------------------
# [STEP 6] Python workspace (inside LXC)
# ---------------------------------------------------------------------------
# TODO: cd "$INSTALL_DIR" && uv sync

# ---------------------------------------------------------------------------
# [STEP 7] Frontend build (inside LXC)
# ---------------------------------------------------------------------------
# TODO: cd "$INSTALL_DIR/packages/dashboard" && pnpm install && pnpm build

# ---------------------------------------------------------------------------
# [STEP 8] PostgreSQL — create database and user (inside LXC)
# ---------------------------------------------------------------------------
# TODO: createdb "$DB_NAME"; createuser "$DB_USER"

# ---------------------------------------------------------------------------
# [STEP 9] Database migrations (inside LXC)
# ---------------------------------------------------------------------------
# TODO: cd "$INSTALL_DIR" && uv run alembic upgrade head

# ---------------------------------------------------------------------------
# [STEP 10] systemd units (inside LXC)
# ---------------------------------------------------------------------------
# TODO: install and enable agent-scout, beacon, watchtower, dashboard units

echo "AgentSentry LXC install stub complete. Implement steps above for Phase 6."
