"""Compact graph state. Never place a chat transcript or raw metric series here."""

from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel, Field


class Hypothesis(BaseModel):
    root_cause: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[str]
    counter_evidence: list[str]
    recommended_actions: list[str]
    citation_ids: list[str]


class Remediation(BaseModel):
    artifact_type: str = "issue"
    title: str
    body: str
    labels: list[str] = Field(default_factory=list)
    github_url: str | None = None
    status: str = "pending"


class IncidentState(TypedDict, total=False):
    incident_id: str
    scenario_id: str | None
    metrics_snapshot: dict[str, object]
    anomaly: dict[str, object] | None
    retrieved_chunks: list[dict[str, object]]
    github_context: dict[str, object]
    evidence_pack: dict[str, object]
    hypothesis: dict[str, object] | None
    remediation: dict[str, object] | None
    trace_notes: list[str]
    error: str | None
    llm_calls: int
    status: str
