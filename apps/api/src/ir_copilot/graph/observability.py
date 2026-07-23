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

        return [CallbackHandler(public_key=settings.langfuse_public_key)]
    except ImportError:
        return []


def finalize_langfuse_run(callbacks: list[object], result: dict[str, object]) -> None:
    """Best-effort final metadata; tracing must never affect an incident result."""
    metadata = {
        "scenario_id": result.get("scenario_id"),
        "incident_id": result.get("incident_id"),
        "status": result.get("status"),
        "llm_calls": result.get("llm_calls"),
    }
    for callback in callbacks:
        client = getattr(callback, "_langfuse_client", None)
        if client is None:
            continue
        try:
            client.update_current_span(metadata=metadata)
        except Exception:
            continue
