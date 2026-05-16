"""pip subprocess wrapper, plugin entry point discovery, and isolated migration runner.

Plugin alembic migrations are executed in a *separate Python subprocess*
(``app.plugins._migration_runner``). This was a deliberate redesign to avoid:

  * Nested ``asyncio.run()`` inside ``asyncio.to_thread`` — interacted badly
    with asyncpg + greenlet on Windows and could hang inside a transaction.
  * Sharing the main app's ``alembic_version`` table between plugins —
    snapshot/restore tricks corrupted state when more than one plugin existed.

Each plugin now owns ``alembic_version_<plugin_name>`` and migrations run with
a clean sync psycopg2 engine in a child process. The main app's event loop is
never touched.
"""
import asyncio
import importlib
import importlib.metadata
import importlib.util
import logging
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from packaging.utils import canonicalize_name

logger = logging.getLogger(__name__)

# backend/ root — the cwd we hand to the migration subprocess so it can
# import `app.plugins._migration_runner` and `app.core.config`.
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


# ── pip wrappers ─────────────────────────────────────────────────────────────

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


# ── Plugin migrations (subprocess-isolated) ──────────────────────────────────

async def _run_migration_subprocess(
    plugin_name: str,
    plugin_dir: Path,
    action: str,
    on_line: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Spawn ``python -m app.plugins._migration_runner`` and stream its output.

    Returns (success, combined_output). Hard timeout 5 min — a single plugin
    migration that runs longer than that is almost certainly stuck.
    """
    versions_dir = plugin_dir / "migrations" / "versions"
    if not versions_dir.is_dir():
        return True, "no migrations"

    cmd = [
        sys.executable,
        "-m",
        "app.plugins._migration_runner",
        plugin_name,
        str(plugin_dir),
        action,
    ]

    def _run() -> tuple[bool, str]:
        proc = subprocess.Popen(
            cmd,
            cwd=str(_BACKEND_DIR),
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
        try:
            proc.wait(timeout=300)
        except subprocess.TimeoutExpired:
            proc.kill()
            output_lines.append("ERROR: migration subprocess exceeded 300s timeout, killed")
            return False, "\n".join(output_lines)
        return proc.returncode == 0, "\n".join(output_lines)

    return await asyncio.to_thread(_run)


async def run_plugin_migrations(
    plugin_name: str,
    plugin_dir: Path,
    on_line: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Apply a plugin's migrations to head in an isolated subprocess."""
    return await _run_migration_subprocess(plugin_name, plugin_dir, "upgrade", on_line)


async def run_plugin_downgrade(
    plugin_name: str,
    plugin_dir: Path,
    on_line: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Downgrade a plugin's migrations to base (drops its tables) in an isolated subprocess.

    Must be called before pip_uninstall while the package is still importable.
    """
    return await _run_migration_subprocess(plugin_name, plugin_dir, "downgrade", on_line)


# ── Entry point discovery ────────────────────────────────────────────────────

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
