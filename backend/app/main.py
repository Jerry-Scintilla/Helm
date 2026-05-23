from contextlib import asynccontextmanager
import logging
import logging.config
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings

logger = logging.getLogger(__name__)

logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(levelname)s:     %(name)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "app": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
})
from app.core.database import AsyncSessionLocal
from app.core.permissions import seed_permissions
from app.routers import auth, characters, admin, admin_tasks, corporations, alliances, api_tokens
from app.routers.market import router as market_router
from app.routers.admin_market import router as admin_market_router
from app.routers.plugins import public_router as plugins_public_router, router as plugins_router
from app.routers.plugin_ui import router as plugin_ui_router
from app.routers.setup import router as setup_router
from app.plugins.loader import load_plugins
from app.plugins.events import stop_listener



async def _maybe_print_setup_link() -> None:
    """On first boot (no superuser yet), generate and log a one-time admin setup URL."""
    from app.core.setup_token import generate_setup_token, has_any_superuser
    async with AsyncSessionLocal() as db:
        if await has_any_superuser(db):
            return
    token = await generate_setup_token()
    url = f"{settings.app_url}/setup/superuser/{token}"
    banner = "=" * 70
    logger.warning(banner)
    logger.warning("HELM SETUP: No superuser found.")
    logger.warning("Log in via EVE SSO, then open the following URL in your browser:")
    logger.warning("")
    logger.warning("  %s", url)
    logger.warning("")
    logger.warning("This link is single-use and expires in 24 hours.")
    logger.warning("To regenerate: docker exec helm-backend-1 /app/.venv/bin/python -m cli admin setup-link")
    logger.warning(banner)


async def _ensure_default_bucket() -> None:
    """Create a default bucket on first startup if none exist."""
    from sqlalchemy import select, func
    from app.models.bucket import Bucket
    async with AsyncSessionLocal() as db:
        count = (await db.execute(select(func.count()).select_from(Bucket))).scalar()
        if count == 0:
            db.add(Bucket(name="default", capacity=100, description="Default ESI refresh bucket"))
            await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.debug("lifespan startup begin")
    # Startup
    from app.esi.client import register_token_persist
    from app.core.token_persist import persist_refreshed_token
    register_token_persist(persist_refreshed_token)
    async with AsyncSessionLocal() as db:
        await seed_permissions(db)
    await _ensure_default_bucket()
    await _maybe_print_setup_link()
    # 预热 Redis 连接池，避免首次请求时建立连接的延迟
    from app.core.redis import get_pool
    import redis.asyncio as aioredis
    _r = aioredis.Redis(connection_pool=get_pool())
    await _r.ping()
    await _r.aclose()
    logger.debug("calling load_plugins")
    await load_plugins(app)
    logger.debug("lifespan startup complete")
    yield
    # Shutdown
    await stop_listener()


app = FastAPI(
    title=settings.app_name,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://develop.helm.dpdns.org"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class _SlowRequestLogger:
    """Pure-ASGI slow-request logger — avoids BaseHTTPMiddleware's streaming bug."""
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        start = time.perf_counter()
        status_code = 0

        async def _send(message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        await self.app(scope, receive, _send)
        ms = (time.perf_counter() - start) * 1000
        if ms > 2000:
            logger.warning("SLOW %s %s %d %.1fms",
                           scope.get("method", ""), scope.get("path", ""), status_code, ms)

app.add_middleware(_SlowRequestLogger)

app.include_router(auth.router)
app.include_router(characters.router)
app.include_router(corporations.router)
app.include_router(alliances.router)
app.include_router(api_tokens.router)
app.include_router(admin.router)
app.include_router(admin_tasks.router)
app.include_router(market_router)
app.include_router(admin_market_router)
app.include_router(plugins_public_router)
app.include_router(plugins_router)
app.include_router(plugin_ui_router, prefix="/plugin-ui")
app.include_router(setup_router)

# Serve helm-sdk.js for plugin iframes: GET /plugin-sdk/helm-sdk.js
_sdk_dir = Path(__file__).parent / "static"
app.mount("/plugin-sdk", StaticFiles(directory=_sdk_dir), name="plugin-sdk")


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}
