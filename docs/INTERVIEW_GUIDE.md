# IR-Copilot interview guide

These answers describe the implementation in this repository as of Phase 9.

## What was the project?

IR-Copilot is a human-in-the-loop incident-response assistant. It uses classical statistics to decide whether a synthetic metric incident is real, then runs a fixed LangGraph workflow to retrieve runbook context, produce a structured root-cause hypothesis, and create a draft-only GitHub issue or local dry-run artifact. The core promise is: detect with stats, diagnose with agents, remediate with humans.

## What problem does it solve?

During an incident, on-call engineers manually connect metrics, known runbooks, recent changes, and the ticket they need to write. IR-Copilot automates the evidence-gathering and communication portion without letting an LLM decide whether an anomaly exists or make an infrastructure change.

## Walk me through the design.

The React/Vite dashboard calls a small FastAPI API. The API runs the `ScenarioEngine` and `AnomalyDetector`, persists a compact run record in SQLite, and invokes the fixed graph in `apps/api/src/ir_copilot/graph/`. The graph retrieves top runbook chunks from persistent Chroma, optionally reads GitHub context, calls a structured LLM for a hypothesis and draft body, then uses the draft-only GitHub client. The web UI shows metric series, result, trace notes, and the resulting GitHub link or dry-run outbox path.

## How is root cause decided?

There are two separate decisions. `detection/detector.py` first evaluates only the latest metric point against the preceding 30 points using rolling z-score, percent change, and composites such as high error-rate z-score plus `db_pool_util >= 0.9`. Only high-severity results enter the graph. `graph/nodes.py` then builds an EvidencePack from that detector output, up to three retrieved runbook chunks, and bounded GitHub summaries. The hypothesis node validates a Pydantic `Hypothesis` object with a root cause, confidence, evidence, counter-evidence, recommendations, and citations.

## Why LangGraph, and why no supervisor?

Incident response is a known workflow, so the graph is deliberately `gate_on_anomaly → correlate → hypothesize → remediate`. The edges are deterministic in `graph/build.py`; there is no planner or supervisor LLM. This keeps the sequence auditable, makes the golden cases repeatable, and prevents costs from growing with agent loops.

## How do you control hallucination?

The LLM never decides whether a spike is an incident. It receives a compact EvidencePack rather than raw time series, whole runbooks, or unbounded logs. Prompts say to use only supplied evidence, not invent metrics, and not give executable infrastructure-mutation advice. Outputs are Pydantic validated; invalid structured output gets at most one retry. The available action surface has no merge, deploy, kubectl, or delete helper.

## What are the key tradeoffs?

- Synthetic scenarios instead of Prometheus make demos and labels reproducible, but do not prove a production metrics integration.
- A fixed graph is less flexible for novel incidents than an autonomous agent, but it is cheaper and easier to evaluate.
- Issues are the default artifact; a draft PR path accepts only a pre-authored template, which is safer than open-ended code generation.
- Local MiniLM/Chroma is free and private for this small corpus, but weaker than a managed retrieval service on a large messy corpus.
- A PAT is the MVP integration path; a GitHub App would be the production hardening step.

## What problems did you hit, and how did you solve them?

The build was phased so each checkpoint remained runnable. I added `FakeLLM` because detector, graph, GitHub, and API tests must run offline without token spend. Chroma's current embedding-function protocol required explicit query/document methods and local deterministic test embeddings. The dashboard uses Vite proxying to avoid local CORS friction. Docker packaging was written and unit-tested around static serving, but this machine did not have a running Docker daemon, so an image build could not be verified here. Details are in `docs/RETROSPECTIVE.md`.

## How did you control cost?

The configured live model is `gpt-4o-mini` at temperature 0; `AppSettings` rejects other models and caps a graph run at three LLM attempts. Correlation is pure tool orchestration, so a normal high-severity run uses two calls: one hypothesis and one remediation draft. The deterministic noise gate uses zero calls. Local MiniLM embeddings have no API embedding cost. The latest offline `make eval` result was `5/5 exact`, `noise_skip=True`, and `mean_cost=$0.0000` because it uses `FakeLLM`; that is not a claim about a live OpenAI bill. The live golden budget is capped at `$0.03` per scenario.

## How do you know it works?

`make test` currently runs 30 offline tests across detector behavior, RAG retrieval, draft-only GitHub behavior, graph budgets, API routes, static serving, and eval scoring. `make eval` runs five golden scenarios: it produced 5/5 exact root-cause matches with the fake model, and the false-alarm scenario was skipped with zero LLM calls. Langfuse is optional and can trace actual configured runs, but no cloud trace is claimed unless keys are supplied.

## What would you do for a real customer deploy?

I would add a Prometheus `MetricsProvider`, move from a PAT to a GitHub App with installation-scoped permissions, require production API authentication and SSO, use a durable database/object store, define change windows and approved remediation templates, add customer-specific evals, and wire Langfuse projects/retention to the customer's security policy. I would keep the detector/LLM separation and draft-only default while measuring quality on real incident postmortems.

## Why not auto-remediate?

The blast radius is too high for an evidence summary to become an executable action. A bad diagnosis could restart the wrong service, worsen an outage, or violate a change-control policy. IR-Copilot instead drafts the evidence and recommended runbook step so a human owns the final change and the system remains auditable.
