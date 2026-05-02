# AgentSentry

Self-hosted observability suite for local AI coding agents (Claude Code, Cursor, Aider, etc.).
Zero outbound telemetry. All data stays within your infrastructure.

## Architecture

| Module | Role | Stack |
|---|---|---|
| **AgentScout** | Filesystem watcher — incremental delta processing of agent logs | Python, watchdog |
| **The Beacon** | Parser/normalizer — adapter-based vendor format translation | Python |
| **Watchtower** | Backend API + persistence | FastAPI, PostgreSQL 16 |
| **AgentSentry** | Web dashboard — sessions, tokens, costs, tools | Next.js 15, Tailwind v4 |

## Deployment

Three targets, each isolated in its own environment:

- **Bare metal** — `scripts/install.sh`
- **Docker** — `docker compose up -d`
- **Proxmox LXC** — `scripts/install-lxc.sh`

## Who This Is For

Homelabbers and AI power users who want full visibility into their agent usage without sending data to any third party.

## Development Phases

| Phase | Module | Status |
|---|---|---|
| 1: Scaffolding | Repository | In progress |
| 2: AgentScout | Collector | Pending |
| 3: The Beacon | Parser | Pending |
| 4: Watchtower | DB & API | Pending |
| 5: AgentSentry | Frontend | Pending |
| 6: Deployment | Infra | Pending |
| 7: Documentation | README | Pending |
