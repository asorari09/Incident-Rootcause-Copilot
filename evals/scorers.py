"""Small, deterministic scorers for the golden incident scenarios."""

from __future__ import annotations

from typing import Any


def hypothesis_exact_match(expected: str | None, run: dict[str, Any]) -> bool:
    hypothesis = run.get("hypothesis") or {}
    return hypothesis.get("root_cause") == expected


def skipped_without_llm(golden: dict[str, Any], run: dict[str, Any]) -> bool:
    return (
        golden["expected_root_cause"] is None
        and run.get("status") == "skipped"
        and run.get("llm_calls") == 0
    )


def draft_success(golden: dict[str, Any], run: dict[str, Any]) -> bool:
    remediation = run.get("remediation") or {}
    has_draft = bool(remediation.get("github_url")) and remediation.get("status") in {
        "dry_run",
        "created",
        "existing",
    }
    return has_draft if golden["expect_github_draft"] else not has_draft


def estimated_cost_usd(run: dict[str, Any], *, fake_llm: bool) -> float:
    """Fake runs cost zero; live runs use a conservative mini-model budget estimate."""
    return 0.0 if fake_llm else round(float(run.get("llm_calls", 0)) * 0.01, 4)


def score_run(golden: dict[str, Any], run: dict[str, Any], *, fake_llm: bool) -> dict[str, Any]:
    cost = estimated_cost_usd(run, fake_llm=fake_llm)
    return {
        "scenario_id": golden["scenario_id"],
        "status": run.get("status"),
        "expected_root_cause": golden["expected_root_cause"],
        "actual_root_cause": (run.get("hypothesis") or {}).get("root_cause"),
        "hypothesis_exact_match": hypothesis_exact_match(golden["expected_root_cause"], run),
        "llm_calls_used": run.get("llm_calls", 0),
        "llm_calls_within_budget": run.get("llm_calls", 0) <= golden["max_llm_calls"],
        "estimated_cost_usd": cost,
        "cost_within_budget": cost <= golden["max_cost_usd"],
        "skipped_without_llm": skipped_without_llm(golden, run),
        "draft_success": draft_success(golden, run),
    }
