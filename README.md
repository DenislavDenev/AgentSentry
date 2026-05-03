# AgentSentry

Self-hosted observability for local AI coding agents. AgentSentry collects Claude Code session logs from your workstation, parses them in real time, and presents a dashboard showing token usage, tool activity, cache efficiency, and cost — all without sending a single byte to any external service.

---

## Who this is for

- Homelabbers running AI coding agents on one machine and hosting services on another
- Power users of Claude Code who want visibility into token spend across projects and sessions
- Anyone who wants a live view of their AI agent activity without SaaS telemetry

---

## Architecture

```
  Your workstation                    Homelab server (or same machine)
  +-----------------+                 +----------------------------------+
  |  Claude Code    |                 |  AgentSentry                     |
  |                 |  mount (NFS /   |                                  |
  |  ~/.claude/     |  CIFS / LXC     |  AgentScout -----> Watchtower   |
  |    projects/    | ------------->  |  (watcher)  HTTP   (FastAPI)     |
  |    *.jsonl      |                 |                       |           |
  +-----------------+                 |                   PostgreSQL 16  |
                                      |                       |           |
                                      |                   Dashboard       |
                                      |                   (Next.js 15)   |
                                      +----------------------------------+
```

| Component | Role | Stack |
|---|---|---|
| **AgentScout** | Watches the mounted agent log directory, reads new JSONL deltas, POSTs to Watchtower | Python, watchdog |
| **The Beacon** | Pure Python library embedded in AgentScout; parses raw JSONL and deduplicates streaming snapshots | Python |
| **Watchtower** | Receives records, persists them, serves the REST API | FastAPI, asyncpg, PostgreSQL 16 |
| **Dashboard** | 7-view frontend covering overview, sessions, projects, tools, prompts, tips, settings | Next.js 15, Tailwind v4, echarts |

---

## Installation — Docker (fastest path)

**Requirements:** Docker 24+, Docker Compose v2

```bash
git clone https://github.com/DenislavDenev/AgentSentry.git
cd AgentSentry
cp .env.example docker/.env
```

Edit `docker/.env` and set a strong `POSTGRES_PASSWORD`. Then open `docker/docker-compose.yml` and uncomment the agent-scout volume mount, pointing it at your agent log directory:

```yaml
# In the agent-scout service volumes block:
volumes:
  - /path/to/.claude:/data/agent-logs:ro   # <-- your workstation .claude dir
  - scout_state:/var/lib/agentsentry/scout
```

If the logs live on a different machine, mount the NFS/CIFS share on the Docker host first, then use the local mount point as the source path.

```bash
cd docker
docker compose up -d
```

Dashboard: `http://localhost:3000` | API: `http://localhost:8000`

---

## Installation — Bare Metal

**Requirements:** Ubuntu 24.04 LTS or Debian 12

```bash
git clone https://github.com/DenislavDenev/AgentSentry.git
cd AgentSentry

export AGENT_DATA_DIR=/mnt/agent-logs   # path where .claude dir is mounted
export DB_PASS=your-strong-password

sudo -E bash scripts/install.sh
```

The script installs Python 3.12, Node.js 22, PostgreSQL 16, uv, and pnpm; clones the repo to `/opt/agentsentry`; runs Alembic migrations; and registers three systemd units:

| Unit | Check status |
|---|---|
| `agentsentry-watchtower` | `systemctl status agentsentry-watchtower` |
| `agentsentry-scout` | `systemctl status agentsentry-scout` |
| `agentsentry-dashboard` | `systemctl status agentsentry-dashboard` |

---

## Installation — Proxmox LXC

This is the recommended path for homelabbers. Claude Code runs on your workstation; AgentSentry runs in a lightweight LXC on Proxmox VE 8.x.

### 1. Create the LXC

Use the Proxmox UI or `pct` to create an Ubuntu 24.04 or Debian 12 LXC (unprivileged is supported). Recommended sizing: 2 vCPUs, 2 GB RAM, 20 GB disk.

### 2. Expose the agent log directory to the LXC

The `.claude` directory lives on your workstation. Pick one of these options:

**Option A — NFS (workstation exports the share):**
```bash
# On your workstation, add to /etc/exports:
/home/you/.claude  192.168.1.0/24(ro,sync,no_subtree_check)
exportfs -ra

# On the Proxmox host:
mkdir -p /mnt/agent-logs
mount -t nfs 192.168.1.x:/home/you/.claude /mnt/agent-logs
```

**Option B — CIFS/SMB:**
```bash
# On the Proxmox host:
mount -t cifs //192.168.1.x/claude-share /mnt/agent-logs \
  -o ro,credentials=/etc/cifs-credentials
```

**Option C — Bind-mount (workstation IS the Proxmox host):**

No network mount needed. Skip straight to step 3, using your local `.claude` path.

### 3. Add the bind-mount to the LXC config

Add this line to `/etc/pve/lxc/<CTID>.conf` on the Proxmox host:

```
mp0: /mnt/agent-logs,mp=/data/agent-logs,ro=1
```

For Option C, use the local path directly:
```
mp0: /home/you/.claude,mp=/data/agent-logs,ro=1
```

Restart the LXC: `pct stop <CTID> && pct start <CTID>`

### 4. Run the installer inside the LXC

```bash
git clone https://github.com/DenislavDenev/AgentSentry.git
cd AgentSentry

export AGENT_DATA_DIR=/data/agent-logs
export DB_PASS=your-strong-password

sudo -E bash scripts/install-lxc.sh
```

The installer validates the mount before doing anything and aborts with a clear message if it is missing or unreadable.

Dashboard: `http://<LXC-IP>:3000` | API: `http://<LXC-IP>:8000`

---

## Configuring the agent data mount

AgentScout expects this directory layout under `AGENT_DATA_DIR`:

```
AGENT_DATA_DIR/
  projects/
    <project-slug>/
      <session-uuid>.jsonl
      ...
```

This matches exactly what Claude Code writes to `~/.claude/`. Set `AGENT_DATA_DIR` to wherever that directory is accessible on the server.

AgentScout opens all `.jsonl` files in read-only mode and never writes to this path.

---

## Updating

**Bare metal / LXC:**
```bash
cd /opt/agentsentry
sudo -E bash scripts/update.sh
```

`update.sh` runs: `git pull` → `uv sync` → `pnpm build` → `alembic upgrade head` → `systemctl restart`

**Docker:**
```bash
cd AgentSentry/docker
docker compose pull
docker compose up -d --build
```

---

## Troubleshooting

**Dashboard shows "No data" after install**

Verify AgentScout can see the mount and is running:
```bash
systemctl status agentsentry-scout
journalctl -u agentsentry-scout -n 50
ls $AGENT_DATA_DIR/projects/
```

**AgentScout is running but nothing appears in Watchtower**

Check the API directly:
```bash
curl http://localhost:8000/stats/overview
```
If Watchtower is unreachable, check `systemctl status agentsentry-watchtower` and whether PostgreSQL is up (`systemctl status postgresql`).

**Port conflict on 3000 or 8000**

Override before running the installer:
```bash
export DASHBOARD_PORT=3001
export WATCHTOWER_PORT=8080
sudo -E bash scripts/install.sh
```
For Docker, change the `ports:` mappings in `docker-compose.yml`.

**Database migration fails**

Check PostgreSQL is running and the credentials match:
```bash
sudo -u postgres psql -c "\du"
systemctl status postgresql
```

**LXC bind-mount not accessible inside the container**

Check the mount exists on the Proxmox host first, then verify it propagated into the LXC:
```bash
# On Proxmox host:
ls /mnt/agent-logs/projects/

# Inside LXC:
ls /data/agent-logs/projects/
```
If the host path exists but the LXC path is empty, verify the `mp0:` line in `/etc/pve/lxc/<CTID>.conf` and restart the container.

---

## Metrics captured

| Field | Source in Claude Code JSONL |
|---|---|
| Input tokens | `message.usage.input_tokens` |
| Output tokens | `message.usage.output_tokens` |
| Cache read tokens | `message.usage.cache_read_input_tokens` |
| Cache create (5 min) | `message.usage.cache_creation.ephemeral_5m_input_tokens` |
| Cache create (1 hr) | `message.usage.cache_creation.ephemeral_1h_input_tokens` |
| Model | `message.model` |
| Tool name + target | `content[].type == "tool_use"` — name + primary input field |
| Tool result size (est.) | `content[].type == "tool_result"` — character count / 4 |
| Tool errors | `content[].is_error` |
| User prompt text | `message.content` string or text content blocks |
| Session start / end | First and last message timestamp per session |
| Project slug | Derived from the JSONL file path (`projects/<slug>/`) |
| Sidechain flag | `isSidechain` — identifies sub-agent turns |
