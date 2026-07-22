"""The graph's fixed nodes. Correlation is deterministic; only two nodes call an LLM."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ValidationError

from .llm import StructuredLLM
from .state import Hypothesis, IncidentState, Remediation
from .tools import (
    ToolContext,
    get_anomaly_details,
    github_create_draft_issue,
    github_list_recent_commits,
    github_list_recent_issues,
    retrieve_runbooks,
)


class DraftIssue(BaseModel):
    title: str
    body: str
    labels: list[str] = []


def gate_on_anomaly(state: IncidentState) -> dict[str, Any]:
    anomaly = state.get("anomaly") or {}
    if not anomaly.get("is_anomalous") or anomaly.get("severity") != "high":
        return {
            "status": "skipped",
            "llm_calls": 0,
            "trace_notes": [*state.get("trace_notes", []), "gate_on_anomaly: skipped (not high severity)"],
        }
    return {
        "status": "running",
        "trace_notes": [*state.get("trace_notes", []), "gate_on_anomaly: passed"],
    }


def correlate(context: ToolContext):
    def node(state: IncidentState) -> dict[str, Any]:
        anomaly = get_anomaly_details(state)
        query = " ".join(
            str(value)
            for value in (anomaly.get("rule_id"), anomaly.get("metric"), state.get("scenario_id"))
            if value
        )
        chunks = retrieve_runbooks(context, query, k=3)
        github_context = {
            "recent_commits": github_list_recent_commits(context, limit=10),
            "recent_issues": github_list_recent_issues(context, limit=10),
        }
        evidence_pack = {
            "anomaly": anomaly,
            "runbooks": [
                {"id": chunk["id"], "title": chunk["title"], "content": chunk["content"]}
                for chunk in chunks
            ],
            "github_context": github_context,
        }
        return {
            "retrieved_chunks": chunks,
            "github_context": github_context,
            "evidence_pack": evidence_pack,
            "trace_notes": [
                *state.get("trace_notes", []),
                f"correlate: retrieved {len(chunks)} runbook chunks and GitHub context",
            ],
        }

    return node


def hypothesize(llm: StructuredLLM, max_calls: int):
    def node(state: IncidentState) -> dict[str, Any]:
        prompt = (
            "You are diagnosing an incident. Use only provided evidence. Do not invent metrics. "
            "Do not recommend executable infrastructure mutation actions. If evidence is insufficient, say so.\n\n"
            f"EvidencePack:\n{json.dumps(state.get('evidence_pack', {}), sort_keys=True)}"
        )
        hypothesis, calls, error, notes = _structured_call(
            llm, "hypothesize", prompt, Hypothesis, state.get("llm_calls", 0), max_calls
        )
        update: dict[str, Any] = {
            "llm_calls": calls,
            "trace_notes": [*state.get("trace_notes", []), *notes],
        }
        if error:
            update.update({"status": "failed", "error": error})
        else:
            update["hypothesis"] = hypothesis.model_dump()
            update["trace_notes"].append("hypothesize: structured hypothesis created")
        return update

    return node


def remediate(context: ToolContext, llm: StructuredLLM, max_calls: int):
    def node(state: IncidentState) -> dict[str, Any]:
        prompt = (
            "Draft a GitHub issue for human review. Use only provided evidence. Do not invent metrics. "
            "Do not include executable infrastructure mutation instructions. Prefer a safe investigation or "
            "human-approved runbook step.\n\n"
            f"Hypothesis:\n{json.dumps(state.get('hypothesis', {}), sort_keys=True)}\n\n"
            f"EvidencePack:\n{json.dumps(state.get('evidence_pack', {}), sort_keys=True)}"
        )
        draft, calls, error, notes = _structured_call(
            llm, "remediate", prompt, DraftIssue, state.get("llm_calls", 0), max_calls
        )
        update: dict[str, Any] = {
            "llm_calls": calls,
            "trace_notes": [*state.get("trace_notes", []), *notes],
        }
        if error:
            update.update({"status": "failed", "error": error})
            return update
        result = github_create_draft_issue(
            context,
            title=draft.title,
            body=_reasoning_trace(state, draft.body),
            labels=draft.labels,
            incident_id=state["incident_id"],
        )
        remediation = Remediation(
            title=draft.title,
            body=draft.body,
            labels=draft.labels,
            github_url=result.url,
            status=result.status,
        )
        update.update(
            {
                "status": "completed" if result.error is None else "completed_with_github_error",
                "remediation": remediation.model_dump(),
                "error": result.error,
                "trace_notes": [
                    *update["trace_notes"],
                    f"remediate: GitHub draft {result.status}",
                ],
            }
        )
        return update

    return node


def _structured_call(
    llm: StructuredLLM,
    task: str,
    prompt: str,
    schema: type[BaseModel],
    calls_used: int,
    max_calls: int,
) -> tuple[BaseModel | None, int, str | None, list[str]]:
    notes: list[str] = []
    for attempt in range(2):
        if calls_used >= max_calls:
            return None, calls_used, "budget_exceeded", [*notes, f"{task}: budget exceeded"]
        calls_used += 1
        try:
            payload = llm.generate_json(task, prompt, schema)
            return schema.model_validate(payload), calls_used, None, [*notes, f"{task}: LLM call {calls_used}"]
        except (ValidationError, ValueError, TypeError) as exc:
            notes.append(f"{task}: structured output invalid on attempt {attempt + 1}")
            if attempt == 1:
                return None, calls_used, f"{task}_structured_output_failed: {exc}", notes
        except Exception as exc:  # provider errors fail softly and never escape the graph
            return None, calls_used, f"{task}_failed: {exc}", notes
    raise AssertionError("unreachable")


def _reasoning_trace(state: IncidentState, body: str) -> str:
    hypothesis = state.get("hypothesis") or {}
    anomaly = state.get("anomaly") or {}
    return (
        f"{body.rstrip()}\n\n---\n"
        "## IR-Copilot reasoning trace\n\n"
        f"- Detector rule: {anomaly.get('rule_id')}\n"
        f"- Detector score: {anomaly.get('score')}\n"
        f"- Hypothesis: {hypothesis.get('root_cause')}\n"
        f"- Model policy: gpt-4o-mini, temperature 0\n"
    )
