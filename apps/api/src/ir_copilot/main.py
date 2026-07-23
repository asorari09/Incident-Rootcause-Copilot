"""FastAPI entry point for detector and fixed-graph incident runs."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ir_copilot.api.routes import build_router
from ir_copilot.api.settings import ApiSettings
from ir_copilot.api.store import IncidentRepository


def create_app(
    *,
    database_path: Path | None = None,
    api_settings: ApiSettings | None = None,
    web_dist: Path | None = None,
) -> FastAPI:
    app = FastAPI(title="IR-Copilot API", version="0.1.0")
    repository = IncidentRepository(database_path or Path("data/ir_copilot.sqlite3"))
    app.include_router(build_router(repository=repository, api_settings=api_settings or ApiSettings.from_env()))
    _mount_dashboard(app, web_dist or _default_web_dist())
    return app


def _default_web_dist() -> Path:
    configured = os.getenv("IR_COPILOT_WEB_DIST")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[3] / "web/dist"


def _mount_dashboard(app: FastAPI, web_dist: Path) -> None:
    """Serve the compiled SPA after API routes, or stay API-only during local dev."""
    index_file = web_dist / "index.html"
    if not index_file.is_file():
        return
    assets_dir = web_dist / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="web-assets")

    @app.get("/", include_in_schema=False)
    @app.get("/{spa_path:path}", include_in_schema=False)
    def dashboard(spa_path: str = "") -> FileResponse:
        del spa_path
        return FileResponse(index_file)

app = create_app()
