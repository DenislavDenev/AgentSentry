# AgentSentry

AgentSentry is a small self-hosted dashboard for understanding AI coding agent token usage.

It is built for people who run tools like Claude Code on a personal computer but want an always-on usage dashboard in their homelab. It works in the same spirit as token-dashboard and Observatory: local data, browser-based visibility, and practical insight into what is driving token spend.

AgentSentry reads a mounted agent log directory, stores analytics locally, and serves a browser dashboard.

## Contents

- [Why Use It](#why-use-it)
- [What You Get](#what-you-get)
- [How It Works](#how-it-works)
- [Install With Docker](#install-with-docker)
- [Install On Bare Metal](#install-on-bare-metal)
- [Install In Proxmox LXC](#install-in-proxmox-lxc)
- [Configuration](#configuration)
- [Privacy](#privacy)
- [Troubleshooting](#troubleshooting)

## Why Use It

Use it when you want to know:

- Which prompts are expensive
- Which projects use the most context
- Which tools return huge outputs
- Which files are being read again and again
- Whether prompt caching is helping
- Which models are driving cost
- What habits could reduce token usage

## What You Get

- Live browser dashboard served on port 8000
- Claude Code token usage tracking (reads JSONL logs directly)
- Prompt and session history with billable token attribution
- Project-level usage
- Model usage and API-equivalent cost estimates
- Tool call summaries
- Cache efficiency trends
- Token reduction tips
- Local SQLite storage — no external database required
- Docker, bare metal, and Proxmox LXC installation paths

## How It Works

One Python process does everything: watches the log directory, stores data in SQLite, and serves the browser dashboard.

```text
Personal computer
  ~/.claude/projects   (JSONL session logs)
        |
        | mount read-only
        v
Homelab server
  AgentSentry (single process, port 8000)
    - watchdog file watcher
    - FastAPI JSON API  (/api/*)
    - Vite SPA          (/)
    - SQLite            (/var/lib/agentsentry/agentsentry.db)
```

AgentSentry does not modify your agent logs.

## Install With Docker

Docker is the easiest way to run AgentSentry.

### 1. Mount Your Agent Logs

Mount your personal computer's `.claude` directory on the Docker host. For Claude Code this is the full `.claude` directory, not only `projects/`.

Check that it contains session logs:

```bash
ls /mnt/agent-logs/projects
```

### 2. Create `docker-compose.yml`

```yaml
services:
  watchtower:
    image: ghcr.io/denislavdenev/agentsentry:latest
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - /mnt/agent-logs:/data/agent-logs:ro
      - agentsentry_data:/var/lib/agentsentry
    environment:
      AGENT_DATA_DIR: /data/agent-logs
      # DATABASE_URL and DASHBOARD_DIR are set to sensible defaults in the image.

volumes:
  agentsentry_data:
```

If building from source, the Dockerfile is a multi-stage build — Node builds the Vite SPA, Python carries the result. No separate build step needed:

```yaml
    build:
      context: .
      dockerfile: packages/watchtower/Dockerfile
```

### 3. Start

```bash
docker compose up -d
```

Open `http://SERVER-IP:8000`

## Install On Bare Metal

Supported: Debian 12, Ubuntu 24.04 LTS.

### 1. Mount Your Agent Logs

Make the `.claude` directory accessible at `/data/agent-logs` (or set `AGENT_DATA_DIR` to any path).

### 2. Run the installer

```bash
git clone https://github.com/DenislavDenev/AgentSentry.git
cd AgentSentry
sudo AGENT_DATA_DIR=/data/agent-logs ./scripts/install.sh
```

The installer:
- Installs Python (distro package) and Node.js 20 (build-time only); uv provides the Python 3.12 runtime
- Installs uv and pnpm
- Builds the Vite dashboard
- Creates a single `agentsentry-watchtower` systemd service
- Runs a smoke test against port 8000

### 3. Open The Dashboard

```text
http://SERVER-IP:8000
```

### 4. Check The Service

```bash
systemctl status agentsentry-watchtower
journalctl -u agentsentry-watchtower -f
```

## Install In Proxmox LXC

Recommended homelab setup.

Suggested size:

```text
1 vCPU
512 MB RAM
8 GB disk
Ubuntu 24.04
```

### 1. Mount Logs On The Proxmox Host

```bash
# NFS example
mount -t nfs 192.168.1.x:/export/agent-logs /mnt/agent-logs
```

### 2. Bind Mount Into The LXC

Edit the container config on the Proxmox host:

```bash
nano /etc/pve/lxc/CTID.conf
```

Add (replace `<HOST_PATH>` with the full path to your `.claude` directory on the Proxmox host — the same value you would pass as `AGENT_DATA_HOST` to `agentsentry.sh`):

```text
mp0: <HOST_PATH>,mp=/data/agent-logs,ro=1
```

Example:

```text
mp0: /mnt/agent-logs,mp=/data/agent-logs,ro=1
```

Restart:

```bash
pct restart CTID
```

### 3. Use The Automated Creator (recommended)

Run on the Proxmox host — creates the LXC and runs the installer inside it:

```bash
bash scripts/proxmox/ct/agentsentry.sh
```

### 4. Or Install Manually Inside The LXC

```bash
git clone https://github.com/DenislavDenev/AgentSentry.git
cd AgentSentry
sudo AGENT_DATA_DIR=/data/agent-logs ./scripts/install-lxc.sh
```

Open `http://LXC-IP:8000`

## Configuration

All settings are environment variables passed to the `agentsentry-watchtower` service.

| Variable | Default | Purpose |
|---|---|---|
| `AGENT_DATA_DIR` | `/data/agent-logs` | Mounted agent log directory (Claude Code `.claude` folder) |
| `DATABASE_URL` | `sqlite+aiosqlite:////var/lib/agentsentry/agentsentry.db` | SQLite database path |
| `STATE_DIR` | `/var/lib/agentsentry/scout` | Scout state file directory |
| `DASHBOARD_DIR` | *(auto-set by installer and Docker image)* | Path to built Vite `dist/` folder; set automatically, override only for custom builds |
| `HOST` | `0.0.0.0` | Listen address |
| `PORT` | `8000` | Listen port |

Override in the systemd unit:

```bash
systemctl edit agentsentry-watchtower
# Add under [Service]:
# Environment="PORT=9000"
systemctl restart agentsentry-watchtower
```

## Updating

```bash
cd /opt/agentsentry
sudo ./scripts/update.sh
```

The update script pulls latest code, rebuilds the dashboard, syncs Python deps, and restarts the service. Database migrations run automatically at startup.

## Privacy

AgentSentry is local-first.

It does not upload prompts, send telemetry, require an account, or modify your agent logs. The dashboard may show prompts, file paths, project names, and tool output summaries. If you expose it beyond a trusted LAN, put it behind authentication.

## Troubleshooting

### No Data

Check the mounted logs:

```bash
ls /data/agent-logs/projects
```

Check the stats endpoint:

```bash
curl http://localhost:8000/api/stats/overview
```

### Service Not Starting

```bash
systemctl status agentsentry-watchtower
journalctl -u agentsentry-watchtower -n 100
```

### Port Already In Use

```bash
systemctl edit agentsentry-watchtower
# Add: Environment="PORT=9000"
systemctl restart agentsentry-watchtower
```

### Docker

```bash
docker compose logs watchtower
```
