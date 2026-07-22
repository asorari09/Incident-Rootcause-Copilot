"""Optional Langfuse callback hook; local graph runs work without it."""

from __future__ import annotations

from ir_copilot.config import AppSettings


def langfuse_callbacks(settings: AppSettings) -> list[object]:
    if not (
        settings.langfuse_enabled
        and settings.langfuse_public_key
        and settings.langfuse_secret_key
    ):
        return []
    try:
        from langfuse.langchain import CallbackHandler

        return [CallbackHandler()]
    except ImportError:
        return []
