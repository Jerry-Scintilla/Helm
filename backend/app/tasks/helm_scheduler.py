"""Custom Celery Beat scheduler with dynamic interval overrides AND hot-loaded
plugin schedules, both sourced from Redis.

Two Redis hashes drive this scheduler, polled every RELOAD_INTERVAL seconds:

  OVERRIDES_KEY  ("helm:schedule:overrides")
      field = beat entry name (built-in or plugin)   e.g. "bucket-scheduler"
      value = interval in seconds                     e.g. "120"

  PLUGIN_SCHEDULES_KEY  ("helm:schedule:plugins")  — see app.tasks.plugin_schedules
      field = namespaced plugin entry name           e.g. "monitor:analyze-all"
      value = JSON {task, schedule, options, plugin}

On each reload the scheduler:
  1. Materialises/updates/removes plugin entries in the live schedule (so plugins
     can register periodic tasks without a Beat restart).
  2. Applies interval overrides on top of both built-in and plugin entries.
When anything changes, self._heap is nulled so Celery rebuilds the heap on the
next tick — preserving last_run_at / total_run_count for unchanged entries.

NOTE: In Celery 5.x PersistentScheduler the live entries live in
self._store['entries'] and are exposed via the self.schedule property.
self.data (from base Scheduler.__init__) is always {} and must NOT be used.
"""
import json
import logging
import time

import redis
from celery.beat import PersistentScheduler
from celery.schedules import schedule as celery_schedule

from app.core.config import settings
from app.tasks.plugin_schedules import PLUGIN_SCHEDULES_KEY

logger = logging.getLogger(__name__)

OVERRIDES_KEY = "helm:schedule:overrides"
RELOAD_INTERVAL = 30  # seconds between Redis polls


class HelmBeatScheduler(PersistentScheduler):
    # Class-level state shared within a single Beat process
    _defaults: dict[str, float] = {}        # original (declared) interval per entry
    _applied: dict[str, float] = {}         # currently active override values
    _plugin_applied: set[str] = set()       # plugin entry names currently materialised
    _last_reload: float = 0

    # ------------------------------------------------------------------ #
    # Initialisation                                                       #
    # ------------------------------------------------------------------ #

    def setup_schedule(self) -> None:
        # Snapshot the built-in defaults once before Celery ever modifies them
        if not type(self)._defaults:
            for name, cfg in self.app.conf.beat_schedule.items():
                try:
                    type(self)._defaults[name] = float(cfg["schedule"])
                except (KeyError, TypeError, ValueError):
                    pass
        super().setup_schedule()
        # Pull plugin schedules + overrides immediately so plugin periodic tasks
        # don't wait a full RELOAD_INTERVAL after a Beat (re)start.
        self._reconcile()

    # ------------------------------------------------------------------ #
    # Tick hook                                                            #
    # ------------------------------------------------------------------ #

    def tick(self, *args, **kwargs):
        now = time.monotonic()
        if now - self._last_reload >= RELOAD_INTERVAL:
            if self._reconcile():
                self._heap = None   # force Celery to rebuild the priority heap
            self._last_reload = now
        return super().tick(*args, **kwargs)

    # ------------------------------------------------------------------ #
    # Reconcile                                                            #
    # ------------------------------------------------------------------ #

    def _reconcile(self) -> bool:
        """Read both Redis hashes and apply plugin entries + overrides.

        Returns True if the live schedule changed.
        """
        try:
            r = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2)
            raw_overrides: dict = r.hgetall(OVERRIDES_KEY)
            raw_plugins: dict = r.hgetall(PLUGIN_SCHEDULES_KEY)
            r.close()
        except Exception as exc:
            logger.warning("HelmBeatScheduler: cannot read Redis schedule state: %s", exc)
            return False

        overrides = self._parse_overrides(raw_overrides)
        plugins = self._parse_plugins(raw_plugins)

        changed = self._sync_plugin_entries(plugins, overrides)
        changed |= self._apply_overrides(overrides)
        return changed

    # ── parsing ─────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_overrides(raw: dict) -> dict[str, float]:
        out: dict[str, float] = {}
        for k, v in raw.items():
            try:
                name = k.decode() if isinstance(k, bytes) else k
                out[name] = float(v.decode() if isinstance(v, bytes) else v)
            except (ValueError, AttributeError):
                continue
        return out

    @staticmethod
    def _parse_plugins(raw: dict) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for k, v in raw.items():
            try:
                name = k.decode() if isinstance(k, bytes) else k
                payload = v.decode() if isinstance(v, bytes) else v
                cfg = json.loads(payload)
                cfg["schedule"] = float(cfg["schedule"])
                out[name] = cfg
            except (ValueError, AttributeError, KeyError, TypeError):
                continue
        return out

    # ── plugin entry materialisation ─────────────────────────────────────────

    def _sync_plugin_entries(self, plugins: dict[str, dict], overrides: dict[str, float]) -> bool:
        """Add/update/remove plugin entries in the live schedule. Returns changed."""
        cls = type(self)
        changed = False
        entries = self.schedule  # self._store['entries']

        # Add / update declared plugin entries
        for name, cfg in plugins.items():
            default_secs = cfg["schedule"]
            cls._defaults[name] = default_secs  # so override-reset can restore it
            secs = overrides.get(name, default_secs)
            new_entry = self.Entry(
                name=name,
                task=cfg["task"],
                schedule=celery_schedule(secs),
                options=cfg.get("options") or {},
                app=self.app,
            )
            if name in entries:
                # Only treat as change if the interval actually differs
                existing = entries[name]
                existing_secs = getattr(getattr(existing, "schedule", None), "run_every", None)
                existing_secs = getattr(existing_secs, "total_seconds", lambda: None)()
                if existing_secs != secs:
                    entries[name].update(new_entry)
                    entries[name] = entries[name]
                    changed = True
            else:
                entries[name] = new_entry
                changed = True
                logger.info("HelmBeatScheduler: + plugin entry %s → %gs (task=%s)", name, secs, cfg["task"])

        # Remove plugin entries that disappeared
        for name in cls._plugin_applied - set(plugins):
            if entries.pop(name, None) is not None:
                changed = True
                logger.info("HelmBeatScheduler: − plugin entry %s removed", name)
            cls._defaults.pop(name, None)

        cls._plugin_applied = set(plugins)
        return changed

    # ── interval overrides ────────────────────────────────────────────────────

    def _apply_overrides(self, new_overrides: dict[str, float]) -> bool:
        """Patch entries to overridden intervals; restore defaults for removed ones."""
        cls = type(self)
        if new_overrides == cls._applied:
            return False

        for name, secs in new_overrides.items():
            self._patch_entry(name, secs)

        # Restore entries whose overrides were removed
        for name in list(cls._applied):
            if name not in new_overrides:
                default = cls._defaults.get(name)
                if default is not None:
                    self._patch_entry(name, default)
                    logger.info("HelmBeatScheduler: %s reset to default %gs", name, default)

        cls._applied = new_overrides
        return True

    def _patch_entry(self, name: str, secs: float) -> None:
        """Update a live schedule entry's interval and keep conf in sync."""
        entries = self.schedule  # self._store['entries']
        if name not in entries:
            logger.warning("HelmBeatScheduler: entry '%s' not found in schedule, skipping", name)
            return
        entry = entries[name]
        entry.schedule = celery_schedule(secs)
        entries[name] = entry  # explicit re-assignment marks the shelve writeback slot dirty
        if name in self.app.conf.beat_schedule:
            self.app.conf.beat_schedule[name]["schedule"] = secs
        logger.info("HelmBeatScheduler: %s → %gs", name, secs)
