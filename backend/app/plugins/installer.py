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
import logging
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from packaging.utils import canonicalize_name

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
    plugin_dir: Path,
    on_line: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Run `alembic upgrade head` inside the plugin's own alembic directory, if present."""
    alembic_ini = plugin_dir / "migrations" / "alembic.ini"
    if not alembic_ini.exists():
        return True, "no migrations"

    def _run() -> tuple[bool, str]:
        proc = subprocess.Popen(
            [sys.executable, "-m", "alembic", "-c", str(alembic_ini), "upgrade", "head"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(plugin_dir / "migrations"),
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
