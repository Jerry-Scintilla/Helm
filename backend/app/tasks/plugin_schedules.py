"""Shared helpers for plugin Beat schedules shipped to Celery Beat via Redis.

Plugins declare periodic tasks through ``HelmPlugin.get_beat_schedule()``.
Because the Celery Beat process is separate from the FastAPI process, schedules
cannot be added by importing code in the API process — Beat reads its schedule
from its own ``app.conf.beat_schedule`` snapshot at startup. So we ship plugin
entries to the running Beat through a Redis hash that ``HelmBeatScheduler``
polls every tick — mirroring the dynamic interval-override mechanism.

Redis hash ``PLUGIN_SCHEDULES_KEY``:
    field = namespaced entry name  ``"{plugin_name}:{local_key}"``
    value = JSON ``{"task": str, "schedule": float, "options": {...}, "plugin": str}``

The FastAPI side (manager/loader) keeps this hash in sync on plugin
install/enable/disable/uninstall and re-pushes all enabled plugins on app
startup, so Beat self-heals even if Redis was flushed.
"""
import json

import redis.asyncio as aioredis

from app.core.redis import get_pool

PLUGIN_SCHEDULES_KEY = "helm:schedule:plugins"


def namespaced_name(plugin_name: str, local_key: str) -> str:
    return f"{plugin_name}:{local_key}"


def serialize_plugin_beat_schedule(plugin) -> dict[str, dict]:
    """Return {namespaced_name: entry_dict} from a plugin's get_beat_schedule().

    Invalid entries (missing task / non-numeric schedule) are skipped with no
    error so one malformed entry can't break a plugin's whole lifecycle.
    """
    out: dict[str, dict] = {}
    try:
        raw = plugin.get_beat_schedule() or {}
    except Exception:
        return out
    for local_key, cfg in raw.items():
        try:
            task = cfg["task"]
            schedule = float(cfg["schedule"])
        except (KeyError, TypeError, ValueError):
            continue
        out[namespaced_name(plugin.name, local_key)] = {
            "task": task,
            "schedule": schedule,
            "options": dict(cfg.get("options") or {}),
            "plugin": plugin.name,
        }
    return out


async def sync_plugin_schedules(entries: dict[str, dict], plugin_name: str) -> None:
    """Replace ``plugin_name``'s entries in the Redis hash (upsert + prune stale)."""
    prefix = f"{plugin_name}:"
    async with aioredis.Redis(connection_pool=get_pool()) as r:
        existing = await r.hkeys(PLUGIN_SCHEDULES_KEY)
        stale = [k for k in existing if k.startswith(prefix) and k not in entries]
        if stale:
            await r.hdel(PLUGIN_SCHEDULES_KEY, *stale)
        if entries:
            await r.hset(
                PLUGIN_SCHEDULES_KEY,
                mapping={k: json.dumps(v) for k, v in entries.items()},
            )


async def remove_plugin_schedules(plugin_name: str) -> None:
    """Drop all of ``plugin_name``'s entries (and their interval overrides)."""
    from app.tasks.helm_scheduler import OVERRIDES_KEY

    prefix = f"{plugin_name}:"
    async with aioredis.Redis(connection_pool=get_pool()) as r:
        for hash_key in (PLUGIN_SCHEDULES_KEY, OVERRIDES_KEY):
            keys = await r.hkeys(hash_key)
            to_del = [k for k in keys if k.startswith(prefix)]
            if to_del:
                await r.hdel(hash_key, *to_del)


async def read_plugin_schedules() -> dict[str, dict]:
    """Read all plugin entries from Redis (used by the admin API)."""
    out: dict[str, dict] = {}
    async with aioredis.Redis(connection_pool=get_pool()) as r:
        raw = await r.hgetall(PLUGIN_SCHEDULES_KEY)
    for name, payload in raw.items():
        try:
            out[name] = json.loads(payload)
        except (ValueError, TypeError):
            continue
    return out
