# Helm — EVE Online Fleet Management

![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)
![Status](https://img.shields.io/badge/status-beta-blue)
![Python](https://img.shields.io/badge/python-3.12+-green)
![Vue](https://img.shields.io/badge/vue-3.5-green)
![Docker](https://img.shields.io/badge/docker-ghcr.io-blue?logo=docker)

**Helm** is a modern, extensible EVE Online corporation and fleet management platform. A thin, fast core handles authentication, ESI data pipelines, and permissions — everything else is delivered through hot-pluggable plugins.

> **Helm is currently in beta (v0.1.0).** Early testers and contributors are welcome!

## Screenshots

![Character Overview](screenshot/%E6%80%BB%E8%A7%88%EF%BC%88%E8%8B%B1%E6%96%87%EF%BC%89.jpeg)

![Skills](screenshot/%E6%8A%80%E8%83%BD%EF%BC%88%E8%8B%B1%E6%96%87%EF%BC%89.jpeg)

![Plugin Management](screenshot/%E6%8F%92%E4%BB%B6%E7%AE%A1%E7%90%86%EF%BC%88%E8%8B%B1%E6%96%87%EF%BC%89.jpeg)

## Documentation

Please refer to the [documentation](https://jerry-scintilla.github.io/Helm-docs/) for installation instructions, architecture details, and the plugin development guide.

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

Browse and install plugins from the **[Plugin Marketplace](https://jerry-scintilla.github.io/Helm-docs/admin-guide/plugin-marketplace/)** — the index is community-maintained and updates in real time.

## Deploy with Docker

> **Prerequisites:** [Docker](https://docs.docker.com/get-docker/) and Docker Compose v2. No other dependencies required.

**1. Download the deployment files**

```bash
curl -O https://raw.githubusercontent.com/Jerry-Scintilla/Helm/master/docker-compose.prod.yml
curl -O https://raw.githubusercontent.com/Jerry-Scintilla/Helm/master/.env.example
cp .env.example .env
```

**2. Fill in `.env`**

```env
POSTGRES_PASSWORD=your_strong_password

APP_SECRET_KEY=your_random_secret_key
APP_URL=http://your-domain             # or http://localhost

EVE_CLIENT_ID=your_eve_client_id       # from developers.eveonline.com
EVE_CLIENT_SECRET=your_eve_client_secret
EVE_CALLBACK_URL=http://your-domain/auth/eve/callback

JWT_SECRET_KEY=your_random_jwt_secret
DB_URL=postgresql+asyncpg://helm:your_strong_password@postgres:5432/helm
```

Register your EVE application at [developers.eveonline.com](https://developers.eveonline.com) and set the callback URL to `http://your-domain/auth/eve/callback`.

**3. Start**

```bash
docker compose -f docker-compose.prod.yml up -d
```

**4. Get the superuser setup link**

On first boot, Helm prints a one-time link to grant admin privileges to the first user. Check the logs:

```bash
docker compose -f docker-compose.prod.yml logs backend | grep "HELM SETUP" -A 8
```

Log in via EVE SSO, then open the printed link in the same browser — admin access is granted instantly, no re-login required.

> Detailed instructions: [Docker Deployment Guide](https://jerry-scintilla.github.io/Helm-docs/getting-started/docker/)

---

## Local Development

**Prerequisites:** Python 3.12+, Node.js 18+, PostgreSQL 14+, Redis 7+

```bash
# Backend
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -e .
copy .env.example .env   # fill in DB, Redis, and EVE SSO credentials
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
# Frontend
cd frontend
npm install
npm run dev
```

## Developing Plugins

Helm plugins are standard Python packages that subclass `HelmPlugin`. They can contribute API routes, SQLAlchemy models, Celery tasks, RBAC permissions, sidebar items, and a compiled Vue frontend.

See the [Plugin Development Guide](https://jerry-scintilla.github.io/Helm-docs/plugin-dev/) to get started.

## Contributing

Bug reports, feature requests, pull requests, and new plugins are all welcome. Open an issue or submit a PR on GitHub.

## Security

If you find a security vulnerability, please email **jerrycaocao@126.com** rather than opening a public issue.

## License

Released under the [GNU General Public License v3.0](LICENSE).
