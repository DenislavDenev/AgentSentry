#!/usr/bin/env bash
# Copyright (c) 2025 AgentSentry Contributors
# License: MIT  https://opensource.org/licenses/MIT
#
# AgentSentry — Proxmox LXC Container Creator
# Run this script ON THE PROXMOX HOST to create CT 111 and install AgentSentry inside it.
#
# Usage:
#   bash agentsentry.sh
#
# Overrideable via env vars:
#   CTID=111 CT_IP=192.168.1.61/24 CT_GW=192.168.1.1 CT_CPU=2 CT_RAM=2048 CT_DISK=20
set -euo pipefail

# ---------------------------------------------------------------------------
# Colour helpers (mirroring community-scripts/ProxmoxVE style)
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
msg_error() { echo -e " ${CROSS} ${RD}$*${CL}"; exit 1; }

header_info() {
  clear
  cat <<'EOF'

    _                    _   ____            _
   / \   __ _  ___ _ __ | |_/ ___|  ___ _ __ | |_ _ __ _   _
  / _ \ / _` |/ _ \ '_ \| __\___ \ / _ \ '_ \| __| '__| | | |
 / ___ \ (_| |  __/ | | | |_ ___) |  __/ | | | |_| |  | |_| |
/_/   \_\__, |\___|_| |_|\__|____/ \___|_| |_|\__|_|   \__, |
         |___/                                          |___/

  Proxmox LXC Installer  —  community-scripts style
EOF
}

# ---------------------------------------------------------------------------
# Default variables
# ---------------------------------------------------------------------------
CTID="${CTID:-111}"
CT_IP="${CT_IP:-192.168.1.61/24}"
CT_GW="${CT_GW:-192.168.1.1}"
CT_HOSTNAME="${CT_HOSTNAME:-agentsentry}"
CT_CPU="${CT_CPU:-2}"
CT_RAM="${CT_RAM:-2048}"
CT_DISK="${CT_DISK:-20}"
CT_OS="${CT_OS:-ubuntu}"
CT_VER="${CT_VER:-24.04}"
CT_STORAGE="${CT_STORAGE:-local-lvm}"
CT_BRIDGE="${CT_BRIDGE:-vmbr0}"
REPO="${REPO:-https://github.com/DenislavDenev/AgentSentry.git}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_SCRIPT="$SCRIPT_DIR/../install/agentsentry-install.sh"

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
header_info

[[ "$(id -u)" -eq 0 ]] || msg_error "Run as root on the Proxmox host."
command -v pct &>/dev/null || msg_error "pct not found — is this a Proxmox host?"
[[ -f "$INSTALL_SCRIPT" ]] || msg_error "Install script not found at $INSTALL_SCRIPT"

if pct status "$CTID" &>/dev/null; then
  msg_error "CT $CTID already exists. Destroy it first: pct destroy $CTID"
fi

# ---------------------------------------------------------------------------
# Prompt for agent data directory (bind-mount source on Proxmox host)
# ---------------------------------------------------------------------------
if [[ -z "${AGENT_DATA_HOST:-}" ]]; then
  echo ""
  echo -e " ${YW}Enter the path on this Proxmox host that contains the .claude agent logs.${CL}"
  echo -e " ${YW}This directory will be bind-mounted read-only into the LXC.${CL}"
  echo -e " ${YW}Example: /mnt/agent-logs  or  /home/user/.claude${CL}"
  echo ""
  read -r -p " AGENT_DATA_DIR (Proxmox host path): " AGENT_DATA_HOST
fi

[[ -d "$AGENT_DATA_HOST" ]] || msg_error "Directory not found: $AGENT_DATA_HOST"

# ---------------------------------------------------------------------------
# Download Ubuntu 24.04 template if not cached
# ---------------------------------------------------------------------------
msg_info "Checking for Ubuntu 24.04 LXC template"
TEMPLATE_STORAGE="${TEMPLATE_STORAGE:-local}"
TEMPLATE=$(pveam list "$TEMPLATE_STORAGE" 2>/dev/null \
  | awk '/ubuntu-24.04-standard/ {print $1; exit}')

if [[ -z "$TEMPLATE" ]]; then
  msg_info "Downloading Ubuntu 24.04 template (this may take a moment)"
  pveam update >/dev/null 2>&1
  REMOTE_TEMPLATE=$(pveam available --section system \
    | awk '/ubuntu-24.04-standard/ {print $2; exit}')
  [[ -n "$REMOTE_TEMPLATE" ]] || msg_error "Ubuntu 24.04 template not found in pveam catalogue."
  pveam download "$TEMPLATE_STORAGE" "$REMOTE_TEMPLATE" >/dev/null 2>&1
  TEMPLATE="${TEMPLATE_STORAGE}:vztmpl/${REMOTE_TEMPLATE}"
  msg_ok "Template downloaded"
else
  msg_ok "Template found: $TEMPLATE"
fi

# ---------------------------------------------------------------------------
# Create the LXC container
# ---------------------------------------------------------------------------
msg_info "Creating LXC container CT $CTID ($CT_HOSTNAME)"

pct create "$CTID" "$TEMPLATE" \
  --hostname  "$CT_HOSTNAME" \
  --cores     "$CT_CPU" \
  --memory    "$CT_RAM" \
  --rootfs    "${CT_STORAGE}:${CT_DISK}" \
  --net0      "name=eth0,bridge=${CT_BRIDGE},ip=${CT_IP},gw=${CT_GW},firewall=0" \
  --ostype    "$CT_OS" \
  --unprivileged 1 \
  --features  "nesting=1" \
  --start     0 \
  >/dev/null 2>&1

msg_ok "Container CT $CTID created"

# ---------------------------------------------------------------------------
# Add read-only bind-mount for agent logs
# ---------------------------------------------------------------------------
msg_info "Adding agent log bind-mount: $AGENT_DATA_HOST -> /data/agent-logs (ro)"
pct set "$CTID" --mp0 "${AGENT_DATA_HOST},mp=/data/agent-logs,ro=1"
msg_ok "Bind-mount configured"

# ---------------------------------------------------------------------------
# Start the container and wait for network
# ---------------------------------------------------------------------------
msg_info "Starting CT $CTID"
pct start "$CTID"

msg_info "Waiting for network inside CT $CTID"
for i in $(seq 1 20); do
  if pct exec "$CTID" -- ping -c1 -W1 8.8.8.8 &>/dev/null; then
    msg_ok "Network ready"
    break
  fi
  if [[ "$i" -eq 20 ]]; then
    msg_error "CT $CTID did not reach the network within 20 s. Check gateway ($CT_GW) and bridge ($CT_BRIDGE)."
  fi
  sleep 1
done

# ---------------------------------------------------------------------------
# Copy and execute the install script inside the container
# ---------------------------------------------------------------------------
msg_info "Pushing install script into CT $CTID"
pct push "$CTID" "$INSTALL_SCRIPT" /root/agentsentry-install.sh
pct exec "$CTID" -- chmod +x /root/agentsentry-install.sh
msg_ok "Install script ready"

msg_info "Running AgentSentry installer inside CT $CTID (this will take several minutes)"
echo ""
pct exec "$CTID" -- bash /root/agentsentry-install.sh

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
IP_PLAIN="${CT_IP%%/*}"
echo ""
msg_ok "AgentSentry installed in CT $CTID"
echo ""
echo -e "  ${GN}Dashboard${CL}  http://${IP_PLAIN}:3000"
echo -e "  ${GN}API      ${CL}  http://${IP_PLAIN}:8000"
echo ""
echo -e "  ${YW}Agent logs are mounted read-only from:${CL} $AGENT_DATA_HOST"
echo ""
