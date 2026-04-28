from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.permissions import seed_permissions
from app.routers import auth, characters, admin, corporations, alliances, api_tokens
from app.routers.plugins import public_router as plugins_public_router, router as plugins_router
from app.plugins.loader import load_plugins
from app.plugins.events import stop_listener


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
    # Startup
    async with AsyncSessionLocal() as db:
        await seed_permissions(db)
    await _ensure_default_bucket()
    await load_plugins(app)
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

app.include_router(auth.router)
app.include_router(characters.router)
app.include_router(corporations.router)
app.include_router(alliances.router)
app.include_router(api_tokens.router)
app.include_router(admin.router)
app.include_router(plugins_public_router)
app.include_router(plugins_router)


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}
