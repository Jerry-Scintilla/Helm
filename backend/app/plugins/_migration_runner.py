"""Standalone subprocess entry point for running a plugin's alembic migrations.

Invoked by `installer.run_plugin_migrations` / `run_plugin_downgrade` as:

    python -m app.plugins._migration_runner <plugin_name> <plugin_dir> <upgrade|downgrade>

Design rules (deliberately decoupled from the main app):

  * Sync psycopg2 driver only — no asyncio, no asyncpg, no greenlet bridging.
    This is the original cause of the hang inside `asyncio.to_thread` +
    nested `asyncio.run()` in the installer.
  * Each plugin gets its own `alembic_version_<plugin_name>` table. The main
    alembic_version table is never touched by plugin migrations, and plugins
    never interfere with each other.
  * The plugin's `migrations/env.py` is NOT invoked. EnvironmentContext is
    driven inline here, so wheels are not required to ship env.py.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from alembic.config import Config
from alembic.runtime.environment import EnvironmentContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, pool

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-5s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("plugin.migrate")


def _sync_db_url() -> str:
    """Return the project DB URL with the async driver swapped out for psycopg2."""
    from app.core.config import settings
    url = settings.db_url
    # postgresql+asyncpg://...  ->  postgresql://...  (psycopg2 default)
    return url.replace("+asyncpg", "")


def _build_fn(script: ScriptDirectory, action: str):
    if action == "upgrade":
        destination = "heads"

        def _upgrade(rev, _ctx):
            return script._upgrade_revs(destination, rev)

        return _upgrade, destination

    if action == "downgrade":
        destination = "base"

        def _downgrade(rev, _ctx):
            return script._downgrade_revs(destination, rev)

        return _downgrade, destination

    raise ValueError(f"unknown action: {action!r}")


def run(plugin_name: str, plugin_dir: Path, action: str) -> int:
    versions_dir = plugin_dir / "migrations" / "versions"
    if not versions_dir.is_dir():
        logger.info("no migrations/versions directory at %s — nothing to do", versions_dir)
        return 0

    cfg = Config()
    cfg.set_main_option("script_location", str(plugin_dir / "migrations"))
    cfg.set_main_option("version_locations", str(versions_dir))

    script = ScriptDirectory.from_config(cfg)
    fn, destination = _build_fn(script, action)

    version_table = f"alembic_version_{plugin_name.replace('-', '_')}"
    logger.info(
        "plugin=%s action=%s version_table=%s versions_dir=%s",
        plugin_name, action, version_table, versions_dir,
    )

    engine = create_engine(_sync_db_url(), poolclass=pool.NullPool, future=True)
    try:
        with engine.connect() as connection:
            with EnvironmentContext(
                cfg,
                script,
                fn=fn,
                as_sql=False,
                destination_rev=destination,
            ) as env:
                env.configure(
                    connection=connection,
                    target_metadata=None,
                    version_table=version_table,
                )
                with env.begin_transaction():
                    env.run_migrations()
    finally:
        engine.dispose()
    logger.info("plugin=%s action=%s DONE", plugin_name, action)
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 4:
        print(
            "usage: _migration_runner <plugin_name> <plugin_dir> <upgrade|downgrade>",
            file=sys.stderr,
        )
        return 2
    plugin_name = argv[1]
    plugin_dir = Path(argv[2])
    action = argv[3]
    try:
        return run(plugin_name, plugin_dir, action)
    except Exception:
        logger.exception("plugin migration FAILED for %s (%s)", plugin_name, action)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
