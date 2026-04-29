from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings
from app.plugins.registry import registry

router = APIRouter(tags=["plugin-ui"])


@router.get("/{plugin_name}/{file_path:path}")
async def serve_plugin_ui(plugin_name: str, file_path: str = ""):
    """Serve static frontend files for an iframe-based plugin.

    In development mode, if the plugin declares a dev server URL, returns 404
    so the browser fetches directly from the plugin's dev server instead.

    For production (or when no dev URL is set), resolves the file from the
    plugin's get_static_dir() and serves it. Falls back to index.html for
    single-page app (SPA) routing.
    """
    plugin = registry.get(plugin_name)
    if plugin is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' is not loaded")

    if settings.app_env == "development":
        dev_url = plugin.get_frontend_dev_url()
        if dev_url:
            raise HTTPException(
                status_code=404,
                detail=f"Plugin '{plugin_name}' is using dev server at {dev_url}",
            )

    static_dir = plugin.get_static_dir()
    if static_dir is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' has no frontend")

    target = (static_dir / file_path) if file_path else (static_dir / "index.html")

    if not target.exists() or not target.is_file():
        # SPA fallback: any unknown path serves index.html
        target = static_dir / "index.html"

    if not target.exists():
        raise HTTPException(status_code=404, detail="index.html not found in plugin frontend")

    return FileResponse(target)
