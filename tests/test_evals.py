"""Offline unit tests for the golden evaluation scoring rules."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))

from scorers import score_run


class EvalScorerTests(unittest.TestCase):
    def test_high_severity_draft_scores_successfully(self) -> None:
        golden = {
            "scenario_id": "sc_db_pool",
            "expected_root_cause": "db_connection_pool_exhaustion",
            "expect_github_draft": True,
            "max_llm_calls": 3,
            "max_cost_usd": 0.03,
        }
        run = {
            "status": "completed",
            "llm_calls": 2,
            "hypothesis": {"root_cause": "db_connection_pool_exhaustion"},
            "remediation": {"status": "dry_run", "github_url": "data/outbox/example.md"},
        }

        score = score_run(golden, run, fake_llm=True)
        self.assertTrue(score["hypothesis_exact_match"])
        self.assertTrue(score["draft_success"])
        self.assertEqual(score["estimated_cost_usd"], 0.0)

    def test_noise_requires_zero_call_skip(self) -> None:
        golden = {
            "scenario_id": "sc_noise_false_alarm",
            "expected_root_cause": None,
            "expect_github_draft": False,
            "max_llm_calls": 0,
            "max_cost_usd": 0.0,
        }
        run = {"status": "skipped", "llm_calls": 0, "hypothesis": None, "remediation": None}

        score = score_run(golden, run, fake_llm=True)
        self.assertTrue(score["hypothesis_exact_match"])
        self.assertTrue(score["skipped_without_llm"])
        self.assertTrue(score["draft_success"])
