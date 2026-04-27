"""Shared utilities for Celery tasks."""
import asyncio
import threading

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.character import Character

DIRECTOR_SCOPE = "esi-corporations.read_corporation_membership.v1"

# A single event loop shared across all tasks in this Celery worker process.
# asyncpg connections are bound to the loop they were created in; reusing one
# persistent loop avoids the 'NoneType has no attribute send' error that occurs
# when asyncio.run() creates and closes a new loop per task on Windows.
_worker_loop: asyncio.AbstractEventLoop | None = None
_worker_loop_lock = threading.Lock()


def _get_worker_loop() -> asyncio.AbstractEventLoop:
    global _worker_loop
    with _worker_loop_lock:
        if _worker_loop is None or _worker_loop.is_closed():
            _worker_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_worker_loop)
        return _worker_loop


async def get_active_characters() -> list[Character]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Character).where(Character.is_active == True)
        )
        return list(result.scalars().all())


async def get_director_characters() -> list[Character]:
    """Return characters that have the corporation director scope."""
    characters = await get_active_characters()
    return [c for c in characters if DIRECTOR_SCOPE in c.scopes.split()]


def run_async(coro):
    """Run a coroutine from a synchronous Celery task using the persistent worker loop."""
    return _get_worker_loop().run_until_complete(coro)
