# Helm — EVE Online Fleet Management

![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)
![Status](https://img.shields.io/badge/status-alpha-orange)
![Python](https://img.shields.io/badge/python-3.12+-green)
![Vue](https://img.shields.io/badge/vue-3.5-green)

**Helm** is a modern, extensible EVE Online fleet management platform built from the ground up. Named after the command center of a spaceship, Helm puts you in control of your corporation's data, pilots, and operations.

> **Helm is currently in alpha development.** No stable releases are available yet. We welcome contributors and early testers!

---

## Core Philosophy: Minimal Core, Infinite Extensibility

Helm is built on a principle of **权衡与搭配** — letting you weigh and combine functionality versus performance according to your needs.

- **Thin, fast host** — Helm core handles only authentication, permissions, ESI data pipelines, and basic entity viewing
- **Powerful plugin system** — All business features (fleet management, killmail tracking, industry planning, etc.) are delivered through hot-pluggable plugins
- **You decide what you need** — Install only the plugins your corporation actually uses; skip the bloat

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic |
| Database | PostgreSQL (MySQL also supported) |
| Task Queue | Celery + Redis |
| ESI Client | Async httpx with stale-while-revalidate caching, ETag, rate-limit backoff |
| Auth | EVE SSO OAuth2 (PKCE), JWT (short-lived access + long-lived refresh) |
| Frontend | Vue 3 (Composition API + `<script setup>`), Vite, Naive UI, Pinia |
| Real-time | Redis PubSub + Server-Sent Events (SSE) |

---

## Key Features

### Core (Built-in)
- **EVE SSO Authentication** — Secure PKCE-based OAuth2 login with JWT tokens
- **Multi-character Management** — Link and manage multiple EVE characters per user
- **ESI Data Pipeline** — Automatic background sync of character, corporation, and alliance data with intelligent caching and rate-limit handling
- **RBAC Permissions** — Fine-grained role-based access control
- **External API Tokens** — Generate scoped API tokens for third-party integrations
- **Character/Corporation/Alliance Viewers** — Wallets, skills, assets, mail, notifications, members, and more

### Plugin System
- **Hot-swappable** — Install, enable, disable, and uninstall plugins without restarting the server
- **Structured SDK** — `HelmPlugin` abstract base class with clear extension points for routers, models, tasks, permissions, and UI
- **Inter-plugin Communication** — `ExtensionRegistry` allows plugins to expose and consume extension points (e.g., MCP tool providers, character submodules)
- **Event Hooks** — Plugins can react to events: `on_character_updated`, `on_corporation_updated`, `on_killmail_received`, etc.
- **Frontend Integration** — Plugins can serve their own Vue frontend via a plugin iframe system

### ESI Client Highlights
- **Stale-while-revalidate** — Returns cached data immediately while refreshing in the background
- **ETag/If-None-Match** — Avoids re-parsing unchanged responses (304 handling)
- **Automatic pagination** — Fetches all pages concurrently
- **Rate-limit backoff** — Exponential backoff with X-ESI-Error-Limit-Remain headers
- **Token refresh** — Automatic ESI token refresh with bucket-based scheduling

---

## Available Plugins

| Plugin | Description | Author |
|--------|-------------|--------|
| [fleet-action](https://github.com/Jerry-Scintilla/helm-plugin-fleet-action) | Fleet PAP (attendance) management with manual record issuance | Jerry_Scintilla |
| [helm-mcp](https://github.com/Jerry-Scintilla/helm-plugin-MCP) | Model Context Protocol server exposing Helm to LLMs | Jerry_Scintilla |

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 14+ (or MySQL 8+)
- Redis 7+

### Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -e .

# Configure environment
copy env.example .env
# Edit .env with your database, Redis, and EVE SSO credentials

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### EVE SSO Setup

1. Create an EVE Online application at [developers.eveonline.com](https://developers.eveonline.com)
2. Set the redirect URI to `http://localhost:8000/api/v1/auth/callback`
3. Add your `CLIENT_ID` and `SECRET_KEY` to the `.env` file

---

## Configuration

Key environment variables (see `.env.example` for full list):

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL/MySQL connection string |
| `REDIS_URL` | Redis connection string |
| `EVE_CLIENT_ID` | EVE Online OAuth client ID |
| `EVE_SECRET_KEY` | EVE Online OAuth secret |
| `EVE_CALLBACK_URL` | OAuth callback URL |
| `HELM_SECRET_KEY` | JWT signing secret (generate a strong random key) |
| `HELM_FRONTEND_DEV_URL` | Frontend dev server URL (default: `http://localhost:5173`) |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   Helm Host Core                     │
│  ┌──────────┐ ┌────────┐ ┌────────┐ ┌──────────┐  │
│  │ Auth/SSO │ │  ESI   │ │  RBAC  │ │  Plugin  │  │
│  │   JWT    │ │ Client │ │  Perm  │ │ Loader   │  │
│  └──────────┘ └────────┘ └────────┘ └──────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │        Celery (Characters / Corps / ESI)     │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
          ▲                        ▲
          │ get_router()           │ get_sidebar_items()
          │ get_tasks()            │ get_character_submodules()
          ▼                        ▼
┌─────────────────────────────────────────────────────┐
│                   Plugin SDK                        │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ HelmPlugin  │  │ ExtensionPt  │  │  Event    │ │
│  │    ABC      │  │  Registry    │  │  Hooks    │ │
│  └─────────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────┘
          ▲                        ▲
          ▼                        ▼
┌─────────────────────────────────────────────────────┐
│              Installed Plugins                      │
│  ┌──────────────┐  ┌──────────────────────────────┐│
│  │ fleet-action │  │       helm-mcp               ││
│  │ (PAP/KM/etc)│  │   (LLM Tool Provider)        ││
│  └──────────────┘  └──────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

---

## Developing Plugins

Helm plugins are standard Python packages that inherit from `HelmPlugin`. A plugin can contribute:

- **API routers** — FastAPI routes mounted at `/api/v1/plugins/{name}/`
- **SQLAlchemy models** — Automatic migration discovery and running
- **Celery tasks** — Registered under plugin-specific queues
- **Permissions** — Seeding into the RBAC system
- **Sidebar items** — Navigation entries in the Helm UI
- **Character submodules** — Sub-pages on character detail pages
- **Frontend** — Compiled Vue app served via plugin iframe

See [Markdown/Plugin_Dev_Guide/](Markdown/Plugin_Dev_Guide/) for a complete plugin development guide.

---

## Contributing

Helm is under active development and we welcome contributions! Whether you're an EVE player who wants a specific feature, a Python developer interested in FastAPI/plugins, or a Vue developer who wants to improve the UI — you're welcome.

**Ways to contribute:**
- Report bugs or request features via GitHub Issues
- Submit pull requests for existing issues
- Develop and publish your own plugins
- Improve documentation

**Development setup** follows the Quick Start section above. All contributions should maintain compatibility with the existing plugin SDK.

---

## License

Helm is released under the **GNU General Public License v3.0 (GPL v3)**.

This means you are free to:
- **Share** — copy and redistribute the software
- **Adapt** — make commercial and private use of the software

Under the following terms:
- **Source must be disclosed** — Any modified versions must be released under the same license
- **Copyright notices must be preserved**
- **Patent conditions apply**

See [LICENSE](LICENSE) for the full license text.

---

## Links

- [Helm Documentation](https://jerry-scintilla.github.io/Helm-docs/)
- [Plugin Development Guide](Markdown/Plugin_Dev_Guide/)
- [EVE Developers Portal](https://developers.eveonline.com)
- [ESI Swagger UI](https://esi.evetech.net/ui/)