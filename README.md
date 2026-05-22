# Helm — EVE Online Fleet Management

![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)
![Status](https://img.shields.io/badge/status-alpha-orange)
![Python](https://img.shields.io/badge/python-3.12+-green)
![Vue](https://img.shields.io/badge/vue-3.5-green)

**Helm** is a modern, extensible EVE Online corporation and fleet management platform. A thin, fast core handles authentication, ESI data pipelines, and permissions — everything else is delivered through hot-pluggable plugins.

> **Helm is currently in alpha.** No stable releases yet. Contributors and early testers welcome!

## Screenshots

![Character Overview](screenshot/%E6%80%BB%E8%A7%88%EF%BC%88%E8%8B%B1%E6%96%87%EF%BC%89.jpeg)

![Skills](screenshot/%E6%8A%80%E8%83%BD%EF%BC%88%E8%8B%B1%E6%96%87%EF%BC%89.jpeg)

![Plugin Management](screenshot/%E6%8F%92%E4%BB%B6%E7%AE%A1%E7%90%86%EF%BC%88%E8%8B%B1%E6%96%87%EF%BC%89.jpeg)

## Documentation

Please refer to the [documentation](https://jerry-scintilla.github.io/Helm-screenshot/) for installation instructions, architecture details, and the plugin development guide.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic |
| Database | PostgreSQL (MySQL supported) |
| Task Queue | Celery + Redis |
| Auth | EVE SSO OAuth2 (PKCE) + JWT |
| Frontend | Vue 3, Vite, Naive UI, Pinia |
| Real-time | Redis PubSub + Server-Sent Events |

## Plugins

| Plugin | Description |
|--------|-------------|
| [fleet-action](https://github.com/Jerry-Scintilla/helm-plugin-fleet-action) | Fleet PAP attendance tracking with manual record issuance |
| [SRP](https://github.com/Jerry-Scintilla/helm-plugin-SRP) | Ship Replacement Program with killmail parsing, officer review, and pricing config |
| [helm-mcp](https://github.com/Jerry-Scintilla/helm-plugin-MCP) | Model Context Protocol server — exposes Helm data to LLMs |

## Quick Start

**Prerequisites:** Python 3.12+, Node.js 18+, PostgreSQL 14+, Redis 7+

```bash
# Backend
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -e .
copy env.example .env   # fill in DB, Redis, and EVE SSO credentials
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
# Frontend
cd frontend
npm install
npm run dev
```

Register your EVE application at [developers.eveonline.com](https://developers.eveonline.com) and set the callback URI to `http://localhost:8000/api/v1/auth/callback`.

## Developing Plugins

Helm plugins are standard Python packages that subclass `HelmPlugin`. They can contribute API routes, SQLAlchemy models, Celery tasks, RBAC permissions, sidebar items, and a compiled Vue frontend.

See the [Plugin Development Guide](Markdown/Plugin_Dev_Guide/) to get started.

## Contributing

Bug reports, feature requests, pull requests, and new plugins are all welcome. Open an issue or submit a PR on GitHub.

## Security

If you find a security vulnerability, please email **jerrycaocao@126.com** rather than opening a public issue.

## License

Released under the [GNU General Public License v3.0](LICENSE).
