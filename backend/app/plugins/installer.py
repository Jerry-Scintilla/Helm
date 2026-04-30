"""
pip subprocess wrapper and plugin entry point discovery.
All functions are async-safe for use inside FastAPI BackgroundTasks.

Note: asyncio.create_subprocess_exec requires ProactorEventLoop on Windows,
which uvicorn does not use. All subprocess calls use subprocess.Popen/run
wrapped in asyncio.to_thread instead — works on all platforms.
"""
import asyncio
import importlib
import importlib.metadata
import io
import logging
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from packaging.utils import canonicalize_name

# Path to the main alembic.ini (backend/alembic.ini), fixed relative to this file.
_ALEMBIC_INI = Path(__file__).parent.parent.parent / "alembic.ini"

logger = logging.getLogger(__name__)


async def pip_install(
    package: str,
    on_line: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Run `pip install <package>`, streaming stdout line-by-line via on_line callback."""
    def _run() -> tuple[bool, str]:
        proc = subprocess.Popen(
            [sys.executable, "-m", "pip", "install", "--no-input", "--disable-pip-version-check", package],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        output_lines: list[str] = []
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.decode(errors="replace").rstrip()
            output_lines.append(line)
            if on_line:
                on_line(line)
        proc.wait()
        return proc.returncode == 0, "\n".join(output_lines)

    return await asyncio.to_thread(_run)


async def pip_uninstall(package: str) -> tuple[bool, str]:
    """Run `pip uninstall -y <package>`."""
    def _run() -> tuple[bool, str]:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", package],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        return result.returncode == 0, result.stdout.decode(errors="replace")

    return await asyncio.to_thread(_run)


async def run_plugin_migrations(
    plugin_name: str,
    plugin_dir: Path,
    on_line: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """
    Upgrade a plugin's migration branch to head using the main alembic context (in-process).

    plugin_name must match the branch_labels value in the plugin's first migration file.
    Runs inside asyncio.to_thread so alembic's internal asyncio.run() gets a fresh loop.
    """
    versions_dir = plugin_dir / "migrations" / "versions"
    if not versions_dir.is_dir():
        return True, "no migrations"

    def _run() -> tuple[bool, str]:
        buf = io.StringIO()
        try:
            cfg = AlembicConfig(str(_ALEMBIC_INI), stdout=buf)
            # env.py normally discovers the plugin via entry_points, but inject here
            # as a fallback in case importlib caches haven't refreshed in this thread.
            existing = cfg.get_main_option("version_locations") or ""
            vs = str(versions_dir)
            if vs not in existing:
                cfg.set_main_option(
                    "version_locations",
                    (existing + os.pathsep + vs) if existing else vs,
                )

            # Snapshot the main branch head revision before plugin migration.
            # Plugin migrations share the alembic_version table row, so we must restore
            # the main branch head after the plugin migration completes.
            from app.core.database import engine
            from sqlalchemy import text

            sync_engine = engine.sync_engine
            with sync_engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                row = result.fetchone()
                main_revision = row[0] if row else None

            alembic_command.upgrade(cfg, f"{plugin_name}@head")

            # Restore main branch revision after plugin migration
            if main_revision:
                with sync_engine.connect() as conn:
                    conn.execute(text("UPDATE alembic_version SET version_num = :rev"), {"rev": main_revision})
                    conn.commit()

            out = buf.getvalue()
            if on_line:
                for line in out.splitlines():
                    on_line(line)
            return True, out or f"upgraded {plugin_name}@head"
        except Exception as exc:
            out = buf.getvalue()
            logger.error("Plugin migration failed for '%s': %s", plugin_name, exc, exc_info=True)
            return False, (f"{out}\n{exc}" if out else str(exc))

    return await asyncio.to_thread(_run)


async def run_plugin_downgrade(
    plugin_name: str,
    plugin_dir: Path,
) -> tuple[bool, str]:
    """
    Downgrade a plugin's migration branch to base (removes all its tables).
    Must be called before pip_uninstall while the package is still importable.
    """
    versions_dir = plugin_dir / "migrations" / "versions"
    if not versions_dir.is_dir():
        return True, "no migrations"

    def _run() -> tuple[bool, str]:
        buf = io.StringIO()
        try:
            cfg = AlembicConfig(str(_ALEMBIC_INI), stdout=buf)
            existing = cfg.get_main_option("version_locations") or ""
            vs = str(versions_dir)
            if vs not in existing:
                cfg.set_main_option(
                    "version_locations",
                    (existing + os.pathsep + vs) if existing else vs,
                )
            alembic_command.downgrade(cfg, f"{plugin_name}@base")
            out = buf.getvalue()
            return True, out or f"downgraded {plugin_name}@base"
        except Exception as exc:
            out = buf.getvalue()
            logger.error("Plugin downgrade failed for '%s': %s", plugin_name, exc, exc_info=True)
            return False, (f"{out}\n{exc}" if out else str(exc))

    return await asyncio.to_thread(_run)


def discover_entry_point(package_name: str) -> tuple[str, Path] | None:
    """
    Find the helm.plugins entry point for the installed package.
    Returns (entry_point_string, plugin_package_dir) or None if not found.
    Package name matching is canonicalized (case-insensitive, - == _).
    """
    # Flush importlib's path cache so packages installed in this process are visible.
    importlib.invalidate_caches()
    canonical = canonicalize_name(package_name)
    for ep in importlib.metadata.entry_points(group="helm.plugins"):
        try:
            dist_name = canonicalize_name(ep.dist.metadata["Name"])
        except Exception:
            continue
        if dist_name != canonical:
            continue
        # Locate the installed package directory
        module_name = ep.value.split(":")[0].split(".")[0]
        spec = importlib.util.find_spec(module_name)
        if spec and spec.submodule_search_locations:
            plugin_dir = Path(list(spec.submodule_search_locations)[0])
        else:
            plugin_dir = Path(str(ep.dist.locate_file(".")))
        return ep.value, plugin_dir
    return None


def load_plugin_class(entry_point: str):
    """Import and return the plugin class from 'module.path:ClassName'."""
    module_path, class_name = entry_point.rsplit(":", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)
