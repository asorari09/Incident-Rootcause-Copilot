"""Offline-first golden scenario evaluator for the fixed incident graph."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ir_copilot.graph.run import fake_llm_for_scenario, run_incident
from scorers import score_run

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = ROOT / "evals/golden.json"
REPORT_PATH = ROOT / "evals/out/report.json"


def run_evals(*, use_fake_llm: bool = True) -> dict[str, Any]:
    golden_cases = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    scores = []
    for golden in golden_cases:
        scenario_id = golden["scenario_id"]
        run = run_incident(
            scenario_id,
            llm=fake_llm_for_scenario(scenario_id) if use_fake_llm else None,
        )
        scores.append(score_run(golden, run, fake_llm=use_fake_llm))

    exact_matches = sum(score["hypothesis_exact_match"] for score in scores)
    noise_score = next(score for score in scores if score["scenario_id"] == "sc_noise_false_alarm")
    passed = (
        exact_matches >= 4
        and noise_score["skipped_without_llm"]
        and all(score["llm_calls_within_budget"] for score in scores)
        and all(score["cost_within_budget"] for score in scores)
        and all(score["draft_success"] for score in scores)
    )
    report = {
        "mode": "fake" if use_fake_llm else "live",
        "passed": passed,
        "summary": {
            "exact_matches": exact_matches,
            "total_scenarios": len(scores),
            "noise_skipped_without_llm": noise_score["skipped_without_llm"],
            "mean_estimated_cost_usd": round(
                sum(score["estimated_cost_usd"] for score in scores) / len(scores), 4
            ),
        },
        "scores": scores,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="use configured gpt-4o-mini instead of FakeLLM")
    args = parser.parse_args()
    report = run_evals(use_fake_llm=not args.live)
    print(
        f"evals {'PASS' if report['passed'] else 'FAIL'}: "
        f"{report['summary']['exact_matches']}/{report['summary']['total_scenarios']} exact, "
        f"noise_skip={report['summary']['noise_skipped_without_llm']}, "
        f"mean_cost=${report['summary']['mean_estimated_cost_usd']:.4f}"
    )
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
