# IR-Copilot architecture

## Runtime shape

```mermaid
flowchart LR
  UI[React + Vite dashboard] -->|REST / proxy| API[FastAPI
main.py + api/routes.py]
  API --> Scenario[ScenarioEngine]
  Scenario --> Store[MetricsStore]
  Store --> Detector[AnomalyDetector
z-score + percent + composites]
  Detector -->|high severity only| Graph[LangGraph fixed pipeline]
  Graph --> RAG[Chroma + local MiniLM
top 3 runbooks]
  Graph --> GH[GitHub client]
  Graph --> SQLite[(SQLite incident runs)]
  GH --> Draft[Draft Issue / local outbox]
  Graph -. optional callbacks .-> Langfuse[Langfuse]
```

The repository ships synthetic metrics only. `apps/api/src/ir_copilot/scenarios/engine.py` produces five reproducible scenarios; `detection/detector.py` evaluates them without importing an LLM client.

## Fixed graph

```mermaid
flowchart LR
  Start --> Gate[gate_on_anomaly
0 LLM calls]
  Gate -->|not high severity| End[END: skipped]
  Gate -->|high severity| Correlate[correlate
tools only]
  Correlate --> Hypothesize[hypothesize
structured LLM call]
  Hypothesize -->|failure/budget| End
  Hypothesize --> Remediate[remediate
structured LLM call + draft tool]
  Remediate --> End
```

`graph/state.py` contains compact fields only: incident/scenario IDs, metric snapshot, anomaly, retrieved chunks, GitHub context, structured result, trace notes, error, and `llm_calls`. The normal path is two calls; the third is reserved for one structured-output retry. `MAX_LLM_CALLS_PER_RUN` cannot exceed three.

## Inject-to-draft sequence

```mermaid
sequenceDiagram
  participant Operator
  participant API as FastAPI
  participant D as Detector
  participant G as Fixed graph
  participant R as Local RAG
  participant H as GitHub / outbox

  Operator->>API: POST /scenarios/sc_db_pool/inject
  API->>D: ScenarioEngine writes MetricsStore
  Operator->>API: POST /incidents/run (use_fake_llm=true)
  API->>D: evaluate()
  D-->>API: high rule.db_pool_saturation
  API->>G: invoke compact IncidentState
  G->>R: retrieve_runbooks(k=3)
  G->>H: list recent context (empty in dry-run)
  G->>G: structured hypothesis + draft
  G->>H: create_draft_issue
  H-->>G: data/outbox path in dry-run
  G-->>API: result + trace_notes
  API-->>Operator: incident record and dashboard data
```

## Deployment boundary

The root `Dockerfile` builds `apps/web` and copies its `dist` output to `/app/web_dist`; `main.py` serves it only when present. API routes are registered first. The first container boot can skip local Chroma indexing for the free demo. `render.yaml` configures the single Docker service and `/health` check used by Render.
