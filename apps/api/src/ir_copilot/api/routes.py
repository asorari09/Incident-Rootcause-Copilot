"""Small, typed REST API over the fixed incident workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from ir_copilot.graph.run import fake_llm_for_scenario, run_incident
from ir_copilot.scenarios import ScenarioEngine

from .settings import ApiSettings
from .store import IncidentRepository


class ScenarioResponse(BaseModel):
    id: str
    description: str
    expected_root_cause: str | None


class InjectResponse(BaseModel):
    scenario_id: str
    metric_names: list[str]
    points_per_metric: dict[str, int]


class IncidentRunRequest(BaseModel):
    scenario_id: str | None = None
    use_fake_llm: bool | None = None


class IncidentRunResponse(BaseModel):
    incident_id: str
    scenario_id: str | None
    metrics_snapshot: dict[str, Any]
    anomaly: dict[str, Any] | None
    hypothesis: dict[str, Any] | None
    remediation: dict[str, Any] | None
    trace_notes: list[str]
    llm_calls: int = Field(ge=0, le=3)
    status: str
    error: str | None = None


class IncidentSummary(BaseModel):
    incident_id: str
    scenario_id: str | None
    status: str
    llm_calls: int
    anomaly: dict[str, Any] | None
    hypothesis: dict[str, Any] | None


def build_router(
    *,
    repository: IncidentRepository,
    api_settings: ApiSettings,
) -> APIRouter:
    router = APIRouter()
    engine = ScenarioEngine()
    injected_stores: dict[str, Any] = {}

    def require_api_key(request: Request) -> None:
        if api_settings.require_api_key and request.headers.get("X-API-KEY") != api_settings.api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid API key")

    @router.get("/health", dependencies=[Depends(require_api_key)])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/scenarios", response_model=list[ScenarioResponse], dependencies=[Depends(require_api_key)])
    def list_scenarios() -> list[ScenarioResponse]:
        scenarios: list[ScenarioResponse] = []
        for scenario_id in engine.list_scenarios():
            definition = engine._load(scenario_id)
            scenarios.append(
                ScenarioResponse(
                    id=scenario_id,
                    description=definition["description"],
                    expected_root_cause=definition["expected_root_cause"],
                )
            )
        return scenarios

    @router.post(
        "/scenarios/{scenario_id}/inject",
        response_model=InjectResponse,
        dependencies=[Depends(require_api_key)],
    )
    def inject_scenario(scenario_id: str) -> InjectResponse:
        from ir_copilot.detection import MetricsStore

        store = MetricsStore()
        try:
            engine.inject(scenario_id, store)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        injected_stores[scenario_id] = store
        return InjectResponse(
            scenario_id=scenario_id,
            metric_names=list(store.metric_names()),
            points_per_metric={name: len(store.window(name)) for name in store.metric_names()},
        )

    @router.get("/metrics/series", dependencies=[Depends(require_api_key)])
    def metric_series(scenario_id: str | None = None, incident_id: str | None = None) -> dict[str, Any]:
        selected_scenario = scenario_id
        if incident_id:
            incident = repository.get(incident_id)
            if incident is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="incident not found")
            selected_scenario = incident.get("scenario_id")
        if not selected_scenario:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="scenario_id or incident_id is required",
            )
        store = injected_stores.get(selected_scenario)
        if store is None:
            from ir_copilot.detection import MetricsStore

            store = MetricsStore()
            try:
                engine.inject(selected_scenario, store)
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return {
            "scenario_id": selected_scenario,
            "series": {
                metric: [
                    {"timestamp": point.timestamp.isoformat(), "value": point.value}
                    for point in store.window(metric)
                ]
                for metric in store.metric_names()
            },
        }

    @router.post(
        "/incidents/run",
        response_model=IncidentRunResponse,
        dependencies=[Depends(require_api_key)],
    )
    def run_incident_route(request: IncidentRunRequest) -> IncidentRunResponse:
        if not request.scenario_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="scenario_id is required")
        use_fake_llm = request.use_fake_llm
        if use_fake_llm is None:
            use_fake_llm = api_settings.default_use_fake_llm
        if use_fake_llm and not api_settings.default_use_fake_llm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="FakeLLM is disabled in this environment; set ALLOW_FAKE_LLM=true for free demos",
            )
        try:
            result = run_incident(
                request.scenario_id,
                metrics_store=injected_stores.get(request.scenario_id),
                llm=fake_llm_for_scenario(request.scenario_id) if use_fake_llm else None,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except Exception as exc:
            if not use_fake_llm and "OPENAI" in str(exc).upper():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Live LLM unavailable; set ALLOW_FAKE_LLM=true for keyless demos",
                ) from exc
            raise
        repository.save(result)
        return IncidentRunResponse.model_validate(result)

    @router.get("/incidents", response_model=list[IncidentSummary], dependencies=[Depends(require_api_key)])
    def list_incidents() -> list[IncidentSummary]:
        return [
            IncidentSummary(
                incident_id=run["incident_id"],
                scenario_id=run.get("scenario_id"),
                status=run["status"],
                llm_calls=run["llm_calls"],
                anomaly=run.get("anomaly"),
                hypothesis=run.get("hypothesis"),
            )
            for run in repository.list_recent()
        ]

    @router.get(
        "/incidents/{incident_id}",
        response_model=IncidentRunResponse,
        dependencies=[Depends(require_api_key)],
    )
    def get_incident(incident_id: str) -> IncidentRunResponse:
        run = repository.get(incident_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="incident not found")
        return IncidentRunResponse.model_validate(run)

    @router.get("/runbooks", dependencies=[Depends(require_api_key)])
    def list_runbooks() -> dict[str, list[str]]:
        return {"runbooks": sorted(path.name for path in engine.scenario_dir.parent.joinpath("runbooks").glob("*.md"))}

    return router
