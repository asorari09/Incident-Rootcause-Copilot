# IR-Copilot

**Detect with stats · Diagnose with agents · Remediate with humans**

[![Live Demo](https://img.shields.io/badge/demo-ir--copilot.onrender.com-0B5FFF?style=flat-square)](https://ir-copilot.onrender.com)
[![Evals](https://img.shields.io/badge/evals-5%2F5%20exact-2ea44f?style=flat-square)](evals/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey?style=flat-square)](LICENSE)

> Live demo on Render Free — first load after idle can take ~1 minute.

---

## Executive summary

When production breaks, on-call engineers must correlate metrics, runbooks, and recent changes — then open a ticket — under time pressure.

**IR-Copilot** is a human-in-the-loop incident assistant that:

1. **Detects anomalies with classical stats** (z-score / thresholds) — the LLM never decides “is this a spike?”
2. **Diagnoses via a fixed LangGraph pipeline** — runbook RAG + structured root-cause hypothesis
3. **Drafts a GitHub issue for human review** — never merges, never mutates infra

| Layer | Choice |
| --- | --- |
| API / UI | FastAPI + React (Vite) |
| Agents | LangGraph (fixed edges, no supervisor) |
| Retrieval | Local MiniLM + Chroma |
| LLM policy | `gpt-4o-mini` only, ≤ 3 calls / run |
| Hosting | One Docker service on [Render Free](https://ir-copilot.onrender.com) |
| Evals | **5/5** golden scenarios; noise path = **0** LLM calls |

---

## System design

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                     Operator Dashboard (React + Vite)                    │
│              inject scenario · metrics · trace · draft link              │
└───────────────────────────────────┬──────────────────────────────────────┘
                                    │ REST
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                              FastAPI                                     │
│         /scenarios  /incidents/run  /metrics  ·  SQLite run store        │
└───────────────────────────────────┬──────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               │
         ┌────────────────────┐                     │
         │  ScenarioEngine    │                     │
         │  synthetic metrics │                     │
         └─────────┬──────────┘                     │
                   ▼                                │
         ┌────────────────────┐                     │
         │ AnomalyDetector    │  ← NO LLM           │
         │ z-score · % change │                     │
         │ composite rules    │                     │
         └─────────┬──────────┘                     │
                   ▼                                │
         ┌────────────────────┐                     │
         │ gate_on_anomaly    │                     │
         └─────────┬──────────┘                     │
           not high│            high severity       │
                   ▼                    ▼           │
            ┌────────────┐    ┌─────────────────┐   │
            │ SKIP       │    │ LangGraph       │   │
            │ 0 LLM calls│    │ correlate       │───┼──► Chroma runbooks
            └────────────┘    │ hypothesize (1) │   │
                              │ remediate   (1) │───┼──► GitHub draft /
                              └────────┬────────┘   │    local outbox
                                       │            │
                                       └────────────┘
```

**Invariant:** stats decide *whether* something is wrong; the model only interprets *grounded evidence* and drafts a reviewable artifact.

---

## Request path

| Step | Component | LLM calls | Result |
| --- | --- | --- | --- |
| 1 | Inject scenario | 0 | Metric series |
| 2 | `AnomalyDetector` | 0 | Severity + rule |
| 3 | `gate_on_anomaly` | 0 | Skip **or** continue |
| 4 | Correlate (tools) | 0 | Evidence pack |
| 5 | Hypothesize | **1** | Structured root cause |
| 6 | Remediate | **1** | Draft issue / outbox file |

---

## Quickstart

```bash
make install && make test
make run-api   # http://127.0.0.1:8000
make run-web   # http://127.0.0.1:5173
```

Or open the [live demo](https://ir-copilot.onrender.com) → select **`sc_db_pool`** → **Inject** → **Run**.

```bash
make eval
# evals PASS: 5/5 exact, noise_skip=True, mean_cost=$0.0000
```

---

## Guardrails

- Fixed graph only — no supervisor, no unbounded agent loops
- Draft-only GitHub (`GITHUB_DRY_RUN=true` by default)
- No merge / deploy / kubectl / cloud-mutation tools
- Model allowlist + hard call budget
- Hosted demo runs keyless via FakeLLM (no paid APIs required)

---

## Docs

- [Demo script](docs/DEMO_SCRIPT.md) — 3- and 8-minute walkthroughs
- [Interview guide](docs/INTERVIEW_GUIDE.md) — what / why / tradeoffs
- [Architecture](docs/ARCHITECTURE.md) · [Decisions](docs/DECISIONS.md) · [Deploy](docs/DEPLOY.md)
- [Retrospective](docs/RETROSPECTIVE.md)
