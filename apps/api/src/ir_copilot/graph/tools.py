"""Thin adapters over detector, local RAG, and the draft-only GitHub client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ir_copilot.github import GitHubClient


class RunbookSearch(Protocol):
    def retrieve(self, query: str, *, top_k: int = 3) -> list[Any]: ...


@dataclass(frozen=True)
class ToolContext:
    github: GitHubClient
    retriever: RunbookSearch | None = None


def get_anomaly_details(state: dict[str, Any]) -> dict[str, object]:
    return dict(state.get("anomaly") or {})


def retrieve_runbooks(context: ToolContext, query: str, k: int = 3) -> list[dict[str, object]]:
    """Best-effort retrieval; never crash the graph if Chroma/MiniLM is unavailable."""
    if context.retriever is None:
        return []
    try:
        chunks = context.retriever.retrieve(query, top_k=k)
    except (OSError, RuntimeError, ValueError):
        return []
    return [
        {
            "id": getattr(chunk, "chunk_id", "runbook:unknown"),
            "source": getattr(chunk, "source", "unknown"),
            "title": getattr(chunk, "title", "unknown"),
            "headers": getattr(chunk, "headers", ""),
            "content": getattr(chunk, "content", "")[:2400],
        }
        for chunk in chunks
    ]


def github_list_recent_commits(context: ToolContext, limit: int = 10) -> list[dict[str, Any]]:
    return context.github.list_recent_commits(limit)


def github_list_recent_issues(context: ToolContext, limit: int = 10) -> list[dict[str, Any]]:
    return context.github.list_recent_issues(limit)


def github_create_draft_issue(
    context: ToolContext,
    *,
    title: str,
    body: str,
    labels: list[str],
    incident_id: str,
):
    return context.github.create_draft_issue(title, body, labels, incident_id=incident_id)
