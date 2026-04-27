from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.permissions import seed_permissions
from app.routers import auth, characters, admin
from app.plugins.loader import load_plugins


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with AsyncSessionLocal() as db:
        await seed_permissions(db)
    await load_plugins(app)
    yield
    # Shutdown (nothing to clean up for now)


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
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}
