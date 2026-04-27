"""Shared utilities for Celery tasks."""
import asyncio
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.esi.client import get_esi_client
from app.models.character import Character


async def get_active_characters() -> list[Character]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Character).where(Character.is_active == True)
        )
        return list(result.scalars().all())


def run_async(coro):
    """Run a coroutine from a synchronous Celery task."""
    return asyncio.run(coro)
