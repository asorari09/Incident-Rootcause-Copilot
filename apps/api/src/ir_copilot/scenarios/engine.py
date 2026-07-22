"""Load repeatable, local scenario definitions into a MetricsStore."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ir_copilot.detection.store import MetricsStore


@dataclass(frozen=True)
class ScenarioInjection:
    scenario_id: str
    expected_root_cause: str | None
    description: str
    log_snippets: tuple[str, ...]
    runbook_hint: str
    patch_template: str | None


class ScenarioEngine:
    """Inject local, deterministic scenario data; no external services are used."""

    def __init__(self, scenario_dir: Path | None = None) -> None:
        self.scenario_dir = scenario_dir or Path(__file__).resolve().parents[5] / "data/scenarios"

    def list_scenarios(self) -> list[str]:
        return sorted(path.stem for path in self.scenario_dir.glob("*.json"))

    def inject(self, scenario_id: str, store: MetricsStore) -> ScenarioInjection:
        definition = self._load(scenario_id)
        store.clear()
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for metric, spec in definition["metrics"].items():
            for offset, value in enumerate(self._series(spec)):
                store.append(metric, start + timedelta(minutes=offset), value)
        return ScenarioInjection(
            scenario_id=definition["id"],
            expected_root_cause=definition["expected_root_cause"],
            description=definition["description"],
            log_snippets=self._log_snippets(definition),
            runbook_hint=definition["runbook_hint"],
            patch_template=definition.get("patch_template"),
        )

    def _load(self, scenario_id: str) -> dict[str, Any]:
        path = self.scenario_dir / f"{scenario_id}.json"
        if not path.is_file():
            raise ValueError(f"unknown scenario: {scenario_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _log_snippets(self, definition: dict[str, Any]) -> tuple[str, ...]:
        log_path = self.scenario_dir / definition["log_file"]
        return tuple(
            line.strip()
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )

    @staticmethod
    def _series(spec: dict[str, Any]) -> list[float]:
        points = int(spec.get("points", 40))
        event_values = [float(value) for value in spec.get("event_values", [])]
        baseline_points = points - len(event_values)
        if baseline_points < 1:
            raise ValueError("scenario event_values must leave at least one baseline point")
        baseline = float(spec["baseline"])
        variation = float(spec.get("variation", 0.0))
        trend = float(spec.get("trend_per_point", 0.0))
        pattern = (-1.0, 0.0, 1.0, 0.0)
        values = [
            baseline + trend * index + variation * pattern[index % len(pattern)]
            for index in range(baseline_points)
        ]
        return values + event_values
