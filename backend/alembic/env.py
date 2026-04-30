import asyncio
import importlib.metadata
import importlib.util
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Add backend/ to sys.path so app imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import settings
from app.core.database import Base
import app.models  # noqa: F401 — registers all models with Base.metadata

config = context.config
config.set_main_option("sqlalchemy.url", settings.db_url)

# Discover all installed helm plugins and add their migration version directories
_main_versions = os.path.join(os.path.dirname(__file__), "versions")
_extra_version_paths: list[str] = []

importlib.invalidate_caches()  # ensure packages installed in this process are visible
for _ep in importlib.metadata.entry_points(group="helm.plugins"):
    try:
        _module_name = _ep.value.split(":")[0].split(".")[0]
        _spec = importlib.util.find_spec(_module_name)
        if _spec and _spec.submodule_search_locations:
            _pkg_root = list(_spec.submodule_search_locations)[0]
            _candidate = os.path.join(_pkg_root, "migrations", "versions")
            if os.path.isdir(_candidate):
                _extra_version_paths.append(_candidate)
    except (ModuleNotFoundError, ValueError, AttributeError):
        pass

if _extra_version_paths:
    existing = config.get_main_option("version_locations") or _main_versions
    all_paths = [existing] + _extra_version_paths
    config.set_main_option("version_locations", os.pathsep.join(all_paths))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
