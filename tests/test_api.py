"""Offline HTTP tests for the Phase 5 FastAPI surface."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from ir_copilot.api.settings import ApiSettings
from ir_copilot.main import create_app


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_dir = tempfile.TemporaryDirectory()
        self.client = TestClient(
            create_app(
                database_path=Path(self.temporary_dir.name) / "runs.sqlite3",
                api_settings=ApiSettings(app_env="development", api_key="dev-key"),
            )
        )

    def tearDown(self) -> None:
        self.temporary_dir.cleanup()

    def test_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_db_pool_inject_and_fake_run(self) -> None:
        injected = self.client.post("/scenarios/sc_db_pool/inject")
        response = self.client.post(
            "/incidents/run", json={"scenario_id": "sc_db_pool", "use_fake_llm": True}
        )

        self.assertEqual(injected.status_code, 200)
        self.assertEqual(response.status_code, 200)
        run = response.json()
        self.assertEqual(run["status"], "completed")
        self.assertEqual(run["hypothesis"]["root_cause"], "db_connection_pool_exhaustion")
        self.assertLessEqual(run["llm_calls"], 3)
        self.assertTrue(run["remediation"]["github_url"])

    def test_noise_run_is_skipped_without_llm(self) -> None:
        response = self.client.post(
            "/incidents/run", json={"scenario_id": "sc_noise_false_alarm", "use_fake_llm": True}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "skipped")
        self.assertEqual(response.json()["llm_calls"], 0)

    def test_incidents_list_and_get_roundtrip(self) -> None:
        run = self.client.post(
            "/incidents/run", json={"scenario_id": "sc_db_pool", "use_fake_llm": True}
        ).json()
        listed = self.client.get("/incidents")
        fetched = self.client.get(f"/incidents/{run['incident_id']}")

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()[0]["incident_id"], run["incident_id"])
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["trace_notes"], run["trace_notes"])

    def test_metrics_are_available_by_scenario_and_incident(self) -> None:
        by_scenario = self.client.get("/metrics/series?scenario_id=sc_db_pool")
        run = self.client.post(
            "/incidents/run", json={"scenario_id": "sc_db_pool", "use_fake_llm": True}
        ).json()
        by_incident = self.client.get(f"/metrics/series?incident_id={run['incident_id']}")

        self.assertIn("error_rate", by_scenario.json()["series"])
        self.assertEqual(by_incident.json()["scenario_id"], "sc_db_pool")


class ApiAuthenticationTests(unittest.TestCase):
    def test_api_key_is_required_outside_development(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            client = TestClient(
                create_app(
                    database_path=Path(root) / "runs.sqlite3",
                    api_settings=ApiSettings(app_env="production", api_key="expected-key"),
                )
            )
            denied = client.get("/health")
            allowed = client.get("/health", headers={"X-API-KEY": "expected-key"})

        self.assertEqual(denied.status_code, 401)
        self.assertEqual(allowed.status_code, 200)
