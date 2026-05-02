#!/usr/bin/env bash
# AgentSentry — Bare-Metal Installer
# Tested on: Ubuntu 24.04 LTS, Debian 12
set -euo pipefail

# ---------------------------------------------------------------------------
# CONFIGURATION — edit these before running
# ---------------------------------------------------------------------------
AGENT_DATA_DIR="${AGENT_DATA_DIR:-/opt/agent-data}"   # Path where agent logs are mounted/accessible
INSTALL_DIR="${INSTALL_DIR:-/opt/agentsentry}"
DB_NAME="${DB_NAME:-agentsentry}"
DB_USER="${DB_USER:-agentsentry}"
DB_PASS="${DB_PASS:-changeme}"                          # Change before production use

# ---------------------------------------------------------------------------
# [STEP 1] System dependencies
# ---------------------------------------------------------------------------
# TODO: apt-get install -y python3.12 python3.12-venv nodejs npm postgresql-16

# ---------------------------------------------------------------------------
# [STEP 2] Install uv
# ---------------------------------------------------------------------------
# TODO: curl -LsSf https://astral.sh/uv/install.sh | sh

# ---------------------------------------------------------------------------
# [STEP 3] Install pnpm
# ---------------------------------------------------------------------------
# TODO: npm install -g pnpm

# ---------------------------------------------------------------------------
# [STEP 4] Clone / copy application
# ---------------------------------------------------------------------------
# TODO: git clone https://github.com/<org>/AgentSentry "$INSTALL_DIR"

# ---------------------------------------------------------------------------
# [STEP 5] Python workspace — install all packages
# ---------------------------------------------------------------------------
# TODO: cd "$INSTALL_DIR" && uv sync

# ---------------------------------------------------------------------------
# [STEP 6] Frontend — install and build
# ---------------------------------------------------------------------------
# TODO: cd "$INSTALL_DIR/packages/dashboard" && pnpm install && pnpm build

# ---------------------------------------------------------------------------
# [STEP 7] PostgreSQL — create database and user
# ---------------------------------------------------------------------------
# TODO: createdb "$DB_NAME"; createuser "$DB_USER"

# ---------------------------------------------------------------------------
# [STEP 8] Database migrations (Alembic)
# ---------------------------------------------------------------------------
# TODO: cd "$INSTALL_DIR" && uv run alembic upgrade head

# ---------------------------------------------------------------------------
# [STEP 9] systemd units — agent-scout, beacon, watchtower, dashboard
# ---------------------------------------------------------------------------
# TODO: install unit files to /etc/systemd/system/ and enable them

echo "AgentSentry install stub complete. Implement steps above for Phase 6."
