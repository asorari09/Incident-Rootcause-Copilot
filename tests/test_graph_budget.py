"""Offline checks for fixed graph routing, hard LLM budgets, and draft-only output."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from ir_copilot.config import AppSettings
from ir_copilot.github import GitHubClient, GitHubSettings
from ir_copilot.graph.build import GraphDependencies
from ir_copilot.graph.llm import FakeLLM
from ir_copilot.graph.run import run_incident
from ir_copilot.graph.tools import ToolContext


@dataclass(frozen=True)
class Chunk:
    chunk_id: str = "runbook:db-pool.md#0"
    source: str = "db-pool.md"
    title: str = "Database Connection Pool Exhaustion"
    headers: str = "Database Connection Pool Exhaustion | Symptoms"
    content: str = "Connection pool utilization above 90 percent causes timeouts."


class StaticRetriever:
    def retrieve(self, query: str, *, top_k: int = 3) -> list[Chunk]:
        del query
        return [Chunk()][:top_k]


def fake_responses(root_cause: str = "db_connection_pool_exhaustion"):
    return {
        "hypothesize": {
            "root_cause": root_cause,
            "confidence": 0.91,
            "evidence": ["Detector composite rule fired."],
            "counter_evidence": [],
            "recommended_actions": ["Review the matching runbook."],
            "citation_ids": ["runbook:db-pool.md#0"],
        },
        "remediate": {
            "title": "Review database connection pool exhaustion",
            "body": "Draft for human review only.",
            "labels": ["severity:high"],
        },
    }


class GraphBudgetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_dir = tempfile.TemporaryDirectory()
        github = GitHubClient(
            GitHubSettings(
                token=None,
                repository="demo-owner/incident-response-copilot",
                dry_run=True,
                outbox_dir=Path(self.temporary_dir.name) / "outbox",
            )
        )
        self.settings = AppSettings(openai_api_key=None)
        self.tools = ToolContext(github=github, retriever=StaticRetriever())

    def tearDown(self) -> None:
        self.temporary_dir.cleanup()

    def dependencies(self, llm: FakeLLM, *, max_calls: int = 3) -> GraphDependencies:
        settings = AppSettings(openai_api_key=None, max_llm_calls_per_run=max_calls)
        return GraphDependencies(tools=self.tools, llm=llm, settings=settings)

    def test_noise_scenario_skips_graph_with_zero_llm_calls(self) -> None:
        result = run_incident(
            "sc_noise_false_alarm",
            dependencies=self.dependencies(FakeLLM(fake_responses())),
        )

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["llm_calls"], 0)
        self.assertIsNone(result["hypothesis"])

    def test_db_pool_happy_path_is_grounded_and_draft_only(self) -> None:
        result = run_incident(
            "sc_db_pool",
            dependencies=self.dependencies(FakeLLM(fake_responses())),
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["llm_calls"], 2)
        self.assertEqual(result["hypothesis"]["root_cause"], "db_connection_pool_exhaustion")
        draft_path = Path(result["remediation"]["github_url"])
        self.assertTrue(draft_path.is_file())
        self.assertIn("IR-Copilot reasoning trace", draft_path.read_text(encoding="utf-8"))

    def test_invalid_output_cannot_exceed_hard_budget(self) -> None:
        looping_fake = FakeLLM(
            {
                "hypothesize": [{"not": "a hypothesis"}, {"still": "invalid"}],
                "remediate": fake_responses()["remediate"],
            }
        )
        result = run_incident(
            "sc_db_pool", dependencies=self.dependencies(looping_fake, max_calls=1)
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"], "budget_exceeded")
        self.assertEqual(result["llm_calls"], 1)
        self.assertEqual(looping_fake.calls, ["hypothesize"])

    def test_forbidden_model_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            AppSettings(openai_api_key="not-used", openai_model="gpt-4o")

    def test_graph_source_has_no_auto_execution_tools(self) -> None:
        graph_dir = Path(__file__).resolve().parents[1] / "apps/api/src/ir_copilot/graph"
        source = "\n".join(path.read_text(encoding="utf-8") for path in graph_dir.glob("*.py"))
        for forbidden in ("merge_pull_request", "kubectl_", "force_push", "delete_"):
            self.assertNotIn(forbidden, source)
