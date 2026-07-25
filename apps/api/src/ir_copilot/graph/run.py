"""Run the fixed workflow from a golden scenario or an existing MetricsStore."""

from __future__ import annotations

import argparse
import uuid
from pathlib import Path
from typing import Any

from ir_copilot.config import AppSettings
from ir_copilot.detection import AnomalyDetector, MetricsStore
from ir_copilot.github import GitHubClient, GitHubSettings
from ir_copilot.rag.embeddings import MiniLMEmbeddingFunction
from ir_copilot.rag.retriever import RunbookRetriever
from ir_copilot.scenarios import ScenarioEngine

from .build import GraphDependencies, build_graph, default_llm
from .llm import FakeLLM, StructuredLLM
from .observability import finalize_langfuse_run, langfuse_callbacks
from .state import IncidentState
from .tools import ToolContext


def run_incident(
    scenario_id: str | None = None,
    metrics_store: MetricsStore | None = None,
    *,
    dependencies: GraphDependencies | None = None,
    llm: StructuredLLM | None = None,
) -> dict[str, Any]:
    """Invoke the graph; callers can supply offline dependencies for tests."""
    engine = ScenarioEngine()
    store = metrics_store or MetricsStore()
    if scenario_id:
        engine.inject(scenario_id, store)
    anomaly = AnomalyDetector().evaluate(store)
    settings = dependencies.settings if dependencies else AppSettings.from_env()
    if dependencies is None:
        github = GitHubClient(GitHubSettings.from_env())
        # Offline fake runs exercise the graph without loading a local embedding model.
        retriever = None if isinstance(llm, FakeLLM) else _default_retriever()
        dependencies = GraphDependencies(
            tools=ToolContext(github=github, retriever=retriever),
            llm=llm or default_llm(settings),
            settings=settings,
        )
    state: IncidentState = {
        "incident_id": f"inc-{uuid.uuid4().hex[:12]}",
        "scenario_id": scenario_id,
        "metrics_snapshot": {
            metric: store.latest(metric).value
            for metric in store.metric_names()
            if store.latest(metric) is not None
        },
        "anomaly": anomaly.as_dict(),
        "retrieved_chunks": [],
        "github_context": {},
        "hypothesis": None,
        "remediation": None,
        "trace_notes": ["run_incident: started"],
        "error": None,
        "llm_calls": 0,
        "status": "running",
    }
    callbacks = langfuse_callbacks(settings)
    result = build_graph(dependencies).invoke(
        state,
        config={
            "callbacks": callbacks,
            "recursion_limit": 8,
            "metadata": {
                "scenario_id": scenario_id,
                "incident_id": state["incident_id"],
                "langfuse_session_id": state["incident_id"],
                "app_version": settings.app_version,
            },
            "tags": ["ir-copilot", scenario_id or "ad_hoc"],
        },
    )
    output = dict(result)
    finalize_langfuse_run(callbacks, output)
    return output


def _default_retriever() -> RunbookRetriever | None:
    try:
        repo_root = Path(__file__).resolve().parents[5]
        return RunbookRetriever(
            persist_dir=repo_root / "data/chroma", embedding_function=MiniLMEmbeddingFunction()
        )
    except Exception:  # noqa: BLE001 - retrieval is optional for a runnable incident result
        return None


def fake_llm_for_scenario(scenario_id: str) -> FakeLLM:
    root_causes = {
        "sc_db_pool": "db_connection_pool_exhaustion",
        "sc_memory_leak": "memory_leak_after_deploy",
        "sc_bad_deploy": "regressive_deploy",
        "sc_dependency_outage": "upstream_dependency_outage",
    }
    return FakeLLM({
        "hypothesize": {
            "root_cause": root_causes.get(scenario_id, "insufficient_evidence"),
            "confidence": 0.8,
            "evidence": ["Synthetic detector evidence"],
            "counter_evidence": [],
            "recommended_actions": ["Review the matching runbook with an on-call engineer."],
            "citation_ids": [],
        },
        "remediate": {
            "title": f"Draft incident response for {scenario_id}",
            "body": "Human review is required before any change.",
            "labels": ["ir-copilot"],
        },
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--fake", action="store_true", help="use deterministic offline structured responses")
    args = parser.parse_args()
    result = run_incident(args.scenario, llm=fake_llm_for_scenario(args.scenario) if args.fake else None)
    print(f"status={result['status']} llm_calls={result['llm_calls']} error={result.get('error')}")
    if result.get("hypothesis"):
        print(f"root_cause={result['hypothesis']['root_cause']}")
    if result.get("remediation"):
        print(f"draft={result['remediation']['github_url']}")


if __name__ == "__main__":
    main()
