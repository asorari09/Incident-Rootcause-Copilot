"""FastAPI entry point for detector and fixed-graph incident runs."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from ir_copilot.api.routes import build_router
from ir_copilot.api.settings import ApiSettings
from ir_copilot.api.store import IncidentRepository


def create_app(
    *, database_path: Path | None = None, api_settings: ApiSettings | None = None
) -> FastAPI:
    app = FastAPI(title="IR-Copilot API", version="0.1.0")
    repository = IncidentRepository(database_path or Path("data/ir_copilot.sqlite3"))
    app.include_router(build_router(repository=repository, api_settings=api_settings or ApiSettings.from_env()))
    return app

app = create_app()
