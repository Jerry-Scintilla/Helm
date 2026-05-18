"""Custom Celery Beat scheduler with dynamic interval overrides from Redis.

Overrides are stored as a Redis hash at OVERRIDES_KEY:
  field = beat_schedule entry name  (e.g. "bucket-scheduler")
  value = interval in seconds       (e.g. "120")

When a change is detected the scheduler directly patches self.data (the
persistent shelve) entry schedules and nulls self._heap so Celery rebuilds
the heap on the next tick — preserving last_run_at/total_run_count.
"""
import logging
import time

import redis
from celery.beat import PersistentScheduler
from celery.schedules import schedule as celery_schedule

from app.core.config import settings

logger = logging.getLogger(__name__)

OVERRIDES_KEY = "helm:schedule:overrides"
RELOAD_INTERVAL = 30  # seconds between Redis polls


class HelmBeatScheduler(PersistentScheduler):
    # Class-level state shared within a single worker process
    _defaults: dict[str, float] = {}   # original beat_schedule intervals
    _applied: dict[str, float] = {}    # currently active override values
    _last_reload: float = 0

    # ------------------------------------------------------------------ #
    # Initialisation                                                       #
    # ------------------------------------------------------------------ #

    def setup_schedule(self) -> None:
        # Snapshot the original defaults once before Celery ever modifies them
        if not type(self)._defaults:
            for name, cfg in self.app.conf.beat_schedule.items():
                try:
                    type(self)._defaults[name] = float(cfg["schedule"])
                except (KeyError, TypeError, ValueError):
                    pass
        super().setup_schedule()

    # ------------------------------------------------------------------ #
    # Tick hook                                                            #
    # ------------------------------------------------------------------ #

    def tick(self, *args, **kwargs):
        now = time.monotonic()
        if now - self._last_reload >= RELOAD_INTERVAL:
            if self._reload_overrides():
                self._heap = None   # force Celery to rebuild the priority heap
            self._last_reload = now
        return super().tick(*args, **kwargs)

    # ------------------------------------------------------------------ #
    # Override loading                                                     #
    # ------------------------------------------------------------------ #

    def _reload_overrides(self) -> bool:
        """Read Redis overrides, patch self.data entries if changed. Returns True on change."""
        try:
            r = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2)
            raw: dict = r.hgetall(OVERRIDES_KEY)
            r.close()
        except Exception as exc:
            logger.warning("HelmBeatScheduler: cannot read Redis overrides: %s", exc)
            return False

        new_overrides: dict[str, float] = {}
        for k, v in raw.items():
            try:
                name = k.decode() if isinstance(k, bytes) else k
                secs = float(v.decode() if isinstance(v, bytes) else v)
                new_overrides[name] = secs
            except (ValueError, AttributeError):
                continue

        if new_overrides == type(self)._applied:
            return False  # nothing changed

        # Apply new / changed overrides
        for name, secs in new_overrides.items():
            self._patch_entry(name, secs)

        # Restore entries whose overrides were removed
        for name in list(type(self)._applied):
            if name not in new_overrides:
                default = type(self)._defaults.get(name)
                if default is not None:
                    self._patch_entry(name, default)
                    logger.info("HelmBeatScheduler: %s reset to default %gs", name, default)

        type(self)._applied = new_overrides
        return True

    def _patch_entry(self, name: str, secs: float) -> None:
        """Directly update self.data[name].schedule and keep beat_schedule in sync."""
        if name not in self.data:
            return
        entry = self.data[name]
        entry.schedule = celery_schedule(secs)
        self.data[name] = entry  # explicit re-assignment marks shelve entry dirty
        # Keep app.conf in sync so the admin API reports the right value
        if name in self.app.conf.beat_schedule:
            self.app.conf.beat_schedule[name]["schedule"] = secs
        logger.info("HelmBeatScheduler: %s → %gs", name, secs)
