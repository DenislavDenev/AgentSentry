# AgentSentry

AgentSentry is a small self-hosted dashboard for understanding AI coding agent token usage.

It is built for people who run tools like Claude Code on a personal computer, but want an always-on usage dashboard in their homelab. It works in the same spirit as token-dashboard and Observatory: local data, browser-based visibility, and practical insight into what is driving token spend.

AgentSentry reads a mounted agent log directory, stores analytics locally, and shows where tokens are going across prompts, sessions, projects, tools, and models.

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
- [Future Agent Support](#future-agent-support)

## Why Use It

AgentSentry is for people who want more than a total token count.

Use it when you want to know:

- Which prompts are expensive
- Which projects use the most context
- Which tools return huge outputs
- Which files are being read again and again
- Whether prompt caching is helping
- Which models are driving cost
- What habits could reduce token usage

The goal is simple: make token waste visible.

## What You Get

- Live browser dashboard
- Claude Code token usage tracking
- Prompt and session history
- Project-level usage
- Model usage and API-equivalent cost estimates
- Tool call summaries
- Large output and repeated file-read detection
- Cache efficiency trends
- Token reduction tips
- Local SQLite storage
- Docker, bare metal, and Proxmox LXC installation paths

## How It Works

AgentSentry runs on your homelab server, VM, container, or LXC.

Your personal computer shares its agent log directory read-only. AgentSentry reads that mounted directory and serves a local dashboard.

```text
Personal computer
  ~/.claude/projects

Homelab server
  /data/agent-logs/projects

AgentSentry
  reads logs
  stores analytics locally
  serves the dashboard
```

For Claude Code, mount the `.claude` directory itself, not only the `projects` folder.

AgentSentry does not modify your agent logs.

## Install With Docker

Docker is the easiest way to run AgentSentry.

### 1. Mount Your Agent Logs

Mount your personal computer's `.claude` directory on the Docker host.

Example:

```text
/mnt/agent-logs/.claude
```

Check that it contains session logs:

```bash
ls /mnt/agent-logs/.claude/projects
```

### 2. Create `docker-compose.yml`

Use the published image when available:

```yaml
services:
  agentsentry:
    image: ghcr.io/denislavdenev/agentsentry:latest
    container_name: agentsentry
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - /mnt/agent-logs/.claude:/data/agent-logs:ro
      - agentsentry_data:/var/lib/agentsentry
    environment:
      AGENTSENTRY_DATA_DIR: /data/agent-logs
      AGENTSENTRY_DB: /var/lib/agentsentry/agentsentry.db
      AGENTSENTRY_SCAN_INTERVAL: 2

volumes:
  agentsentry_data:
```

If you are building from source instead, replace the `image` line with:

```yaml
    build: .
```

### 3. Start AgentSentry

```bash
docker compose up -d
```

Open:

```text
http://SERVER-IP:8080
```

## Install On Bare Metal

Use this method for a small Linux server or VM.

Recommended systems:

- Debian 12
- Ubuntu 24.04 LTS

### 1. Mount Your Agent Logs

Mount the personal computer's `.claude` directory to:

```text
/data/agent-logs
```

Check:

```bash
ls /data/agent-logs/projects
```

### 2. Install AgentSentry

```bash
git clone https://github.com/DenislavDenev/AgentSentry.git
cd AgentSentry
sudo AGENTSENTRY_DATA_DIR=/data/agent-logs ./scripts/install.sh
```

The installer creates a single `agentsentry` service.

### 3. Open The Dashboard

```text
http://SERVER-IP:8080
```

### 4. Check The Service

```bash
systemctl status agentsentry
```

## Install In Proxmox LXC

This is the recommended homelab setup.

Suggested starting size:

```text
1 vCPU
512 MB RAM
8 GB disk
Debian 12 or Ubuntu 24.04
```

### 1. Mount Logs On The Proxmox Host

Example:

```text
/mnt/agent-logs/.claude
```

Check:

```bash
ls /mnt/agent-logs/.claude/projects
```

### 2. Bind Mount Into The LXC

Edit the container config on the Proxmox host:

```bash
nano /etc/pve/lxc/CTID.conf
```

Add:

```text
mp0: /mnt/agent-logs/.claude,mp=/data/agent-logs,ro=1
```

Restart the container:

```bash
pct restart CTID
```

Inside the LXC, check:

```bash
ls /data/agent-logs/projects
```

### 3. Install AgentSentry

```bash
git clone https://github.com/DenislavDenev/AgentSentry.git
cd AgentSentry
sudo AGENTSENTRY_DATA_DIR=/data/agent-logs ./scripts/install-lxc.sh
```

Open:

```text
http://LXC-IP:8080
```

## Configuration

Most installs only need `AGENTSENTRY_DATA_DIR`.

| Variable | Default | Purpose |
|---|---:|---|
| `AGENTSENTRY_HOST` | `0.0.0.0` | Listen address |
| `AGENTSENTRY_PORT` | `8080` | Dashboard port |
| `AGENTSENTRY_DATA_DIR` | `/data/agent-logs` | Mounted agent log directory |
| `AGENTSENTRY_DB` | `/var/lib/agentsentry/agentsentry.db` | Local database path |
| `AGENTSENTRY_SCAN_INTERVAL` | `2` | Scan interval in seconds |

## Privacy

AgentSentry is local-first.

It does not upload prompts, send telemetry, require an account, or modify your agent logs.

The dashboard may show prompts, file paths, project names, and tool output summaries. If you expose it beyond a trusted LAN, put it behind authentication.

## Troubleshooting

### No Data

Check the mounted logs:

```bash
ls /data/agent-logs/projects
```

Check the app:

```bash
curl http://localhost:8080/api/health
```

### Docker

```bash
docker logs agentsentry
```

### Bare Metal Or LXC

```bash
systemctl status agentsentry
journalctl -u agentsentry -n 100
```

### Port Already In Use

Set another port and restart AgentSentry:

```bash
AGENTSENTRY_PORT=8090
```

## Future Agent Support

AgentSentry starts as a Claude Code usage dashboard, but the design is meant to support more AI coding agents over time.

Future sources can include Codex, Cursor, Aider, OpenCode, or other tools that expose local session data.

Model pricing should stay local and editable, so new models can be added without changing the whole app.

## Project Goal

AgentSentry should stay small enough to run quietly in a homelab and useful enough to change how people work.

It exists to make AI coding usage understandable: what happened, what it cost, and what you can do to waste fewer tokens next time.
