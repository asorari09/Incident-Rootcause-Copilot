"""Offline tests for the deterministic detector and golden scenarios."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ir_copilot.detection import AnomalyDetector, MetricsStore
from ir_copilot.scenarios import ScenarioEngine


class MetricsStoreTests(unittest.TestCase):
    def test_append_and_window_query(self) -> None:
        store = MetricsStore()
        start = datetime(2026, 1, 1, tzinfo=UTC)
        for offset in range(3):
            store.append("error_rate", start + timedelta(minutes=offset), offset / 100)

        points = store.window("error_rate", start=start + timedelta(minutes=1), limit=1)

        self.assertEqual([point.value for point in points], [0.02])


class GoldenScenarioDetectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        cls.engine = ScenarioEngine(repo_root / "data/scenarios")
        cls.detector = AnomalyDetector()

    def evaluate(self, scenario_id: str):
        store = MetricsStore()
        injection = self.engine.inject(scenario_id, store)
        return injection, self.detector.evaluate(store)

    def test_all_golden_scenarios_are_available(self) -> None:
        self.assertEqual(
            self.engine.list_scenarios(),
            [
                "sc_bad_deploy",
                "sc_db_pool",
                "sc_dependency_outage",
                "sc_memory_leak",
                "sc_noise_false_alarm",
            ],
        )

    def test_db_pool_incident_is_high_severity_composite(self) -> None:
        injection, result = self.evaluate("sc_db_pool")

        self.assertEqual(injection.expected_root_cause, "db_connection_pool_exhaustion")
        self.assertTrue(result.is_anomalous)
        self.assertEqual(result.severity, "high")
        self.assertEqual(result.rule_id, "rule.db_pool_saturation")
        self.assertGreaterEqual(result.related_metrics["db_pool_util"], 0.9)

    def test_other_real_incidents_match_composite_rules(self) -> None:
        expected_rules = {
            "sc_memory_leak": "rule.memory_leak",
            "sc_bad_deploy": "rule.latency_regression",
            "sc_dependency_outage": "rule.upstream_dependency",
        }
        for scenario_id, expected_rule in expected_rules.items():
            with self.subTest(scenario_id=scenario_id):
                injection, result = self.evaluate(scenario_id)
                self.assertIsNotNone(injection.expected_root_cause)
                self.assertTrue(result.is_anomalous)
                self.assertEqual(result.severity, "high")
                self.assertEqual(result.rule_id, expected_rule)

    def test_noise_scenario_is_not_a_high_severity_incident(self) -> None:
        injection, result = self.evaluate("sc_noise_false_alarm")

        self.assertIsNone(injection.expected_root_cause)
        self.assertFalse(result.is_anomalous)
        self.assertNotEqual(result.severity, "high")

    def test_detector_source_has_no_llm_client_imports(self) -> None:
        detector_source = (
            Path(__file__).resolve().parents[1]
            / "apps/api/src/ir_copilot/detection/detector.py"
        ).read_text(encoding="utf-8").lower()
        for forbidden in ("openai", "langchain", "langgraph", "anthropic"):
            self.assertNotIn(forbidden, detector_source)
