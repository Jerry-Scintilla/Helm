"""
SSE event bus for plugin lifecycle events.

Architecture:
  publish_event() → Redis PubSub channel "helm:plugins:events"
                 → _listener_task fans out to all connected SSE subscribers via asyncio.Queue
"""
import asyncio
import json
import logging
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

CHANNEL = "helm:plugins:events"

# Per-connection subscriber queues
_subscribers: set[asyncio.Queue] = set()

# Dedicated pubsub client (must not share pool with regular commands)
_pubsub_client: aioredis.Redis | None = None
_listener_task: asyncio.Task | None = None


async def start_listener() -> None:
    global _pubsub_client, _listener_task
    _pubsub_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    _listener_task = asyncio.create_task(_run_listener(), name="plugin-sse-listener")
    logger.info("Plugin SSE listener started on channel %s", CHANNEL)


async def stop_listener() -> None:
    global _listener_task, _pubsub_client
    if _listener_task and not _listener_task.done():
        _listener_task.cancel()
        try:
            await _listener_task
        except asyncio.CancelledError:
            pass
    if _pubsub_client:
        await _pubsub_client.aclose()
    _listener_task = None
    _pubsub_client = None
    logger.info("Plugin SSE listener stopped")


async def _run_listener() -> None:
    assert _pubsub_client is not None
    pubsub = _pubsub_client.pubsub()
    await pubsub.subscribe(CHANNEL)
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            data = message["data"]
            dead: set[asyncio.Queue] = set()
            for q in _subscribers:
                try:
                    q.put_nowait(data)
                except asyncio.QueueFull:
                    dead.add(q)
            _subscribers.difference_update(dead)
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(CHANNEL)
        await pubsub.aclose()


async def publish_event(event_type: str, payload: dict) -> None:
    """Publish a plugin lifecycle event to all SSE subscribers."""
    if _pubsub_client is None:
        return
    message = json.dumps({"type": event_type, **payload})
    try:
        await _pubsub_client.publish(CHANNEL, message)
    except Exception as exc:
        logger.warning("Failed to publish plugin event %s: %s", event_type, exc)


async def subscribe() -> AsyncGenerator[str, None]:
    """SSE generator — one per connected client. Yields SSE-formatted strings."""
    q: asyncio.Queue = asyncio.Queue(maxsize=64)
    _subscribers.add(q)
    try:
        while True:
            try:
                data = await asyncio.wait_for(q.get(), timeout=30.0)
                yield f"data: {data}\n\n"
            except asyncio.TimeoutError:
                # keepalive comment
                yield ": keepalive\n\n"
    finally:
        _subscribers.discard(q)
