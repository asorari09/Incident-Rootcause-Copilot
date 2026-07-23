# IR-Copilot

**Detect with stats. Diagnose with agents. Remediate with humans.**

IR-Copilot is a human-in-the-loop incident-response copilot. A deterministic detector decides whether a synthetic metric anomaly is real; a fixed, budget-capped LangGraph workflow then retrieves runbook context, produces a structured hypothesis, and drafts a GitHub issue or local dry-run artifact for human review.

It is intentionally not an auto-remediator, a Datadog replacement, or a free-form multi-agent demo.

## Why it exists

During an outage, engineers have to connect metrics, recent changes, known runbooks, and the incident communication trail under time pressure. IR-Copilot demonstrates a safer division of labor: statistics decide *whether* something is abnormal, and the model helps explain tool-grounded evidence without executing infrastructure changes.

## Architecture

```text
React/Vite dashboard → FastAPI → detector gate → fixed LangGraph
                                      ├→ local MiniLM + Chroma runbooks
                                      └→ draft-only GitHub client / local outbox
```

The full diagram and sequence are in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Quickstart

Requirements: Python 3.12+, [uv](https://docs.astral.sh/uv/), and Node/npm.

```sh
make install
make test
make run-api
```

In a second terminal:

```sh
make run-web
```

Open `http://127.0.0.1:5173`, select `sc_db_pool`, click **Inject**, then **Run incident**. Development uses the offline fake LLM path and Vite proxies API calls to `http://127.0.0.1:8000`. The API OpenAPI UI is at `http://127.0.0.1:8000/docs`.

To index runbooks with the local MiniLM model (when cached/available):

```sh
make index-runbooks
```

## Demo scenarios

| Scenario | Expected result |
|---|---|
| `sc_db_pool` | `db_connection_pool_exhaustion` |
| `sc_memory_leak` | `memory_leak_after_deploy` |
| `sc_bad_deploy` | `regressive_deploy` |
| `sc_dependency_outage` | `upstream_dependency_outage` |
| `sc_noise_false_alarm` | skipped; no root cause |

## Evals and observability

```sh
make eval
```

Latest measured offline result:

```text
evals PASS: 5/5 exact, noise_skip=True, mean_cost=$0.0000
```

This result uses `FakeLLM`, so the zero cost is an offline-test result, not a claim about a live OpenAI bill. Live runs are restricted to `gpt-4o-mini`, temperature 0, and no more than three LLM attempts; the golden live budget is `$0.03/run`. Local MiniLM embeddings have no API embedding cost.

Langfuse is optional. Set `LANGFUSE_ENABLED=true`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and optionally `LANGFUSE_HOST` in an uncommitted `.env` to emit configured traces. Without keys, callbacks are no-ops.

## Guardrails

- The anomaly gate can skip the graph entirely; the noise scenario uses zero LLM calls.
- The graph is fixed, with no supervisor or autonomous agent loop.
- Prompts are grounded in compact detector/RAG/GitHub evidence and structured with Pydantic.
- Only `gpt-4o-mini` is allowed; `MAX_LLM_CALLS_PER_RUN <= 3` is enforced.
- GitHub writes are draft-only. There is no auto-merge, deployment, deletion, kubectl, or cloud mutation tool.
- `GITHUB_DRY_RUN=true` writes Markdown artifacts to `data/outbox/` by default.

## Docker and Railway

For local single-service parity:

```sh
cp .env.example .env
docker compose up --build
```

Then open `http://127.0.0.1:8000/` for the bundled dashboard and
`http://127.0.0.1:8000/health` for the health check. The first boot attempts to
create the local runbook index. Keep `GITHUB_DRY_RUN=true` for public demos.

Railway can deploy the root `Dockerfile` as one service; `railway.toml` declares
the `/health` check. Set variables from `.env.example`, including a production
`API_KEY`; add OpenAI, GitHub, and Langfuse credentials only when intentionally
using those integrations. See [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) for a
live walkthrough.

The Dockerfile and static-serving path are implemented, but this environment did
not have a running Docker daemon, so `docker build` was not verified here.

## Resume-ready bullets

- Built a hybrid incident-response copilot that separates deterministic anomaly detection from LLM diagnosis to reduce hallucination risk.
- Implemented a fixed LangGraph workflow with local runbook retrieval, Pydantic structured outputs, hard per-run call caps, and draft-only GitHub remediation.
- Added five golden scenarios and an offline eval harness that measured 5/5 exact matches with the false-alarm path using zero LLM calls.
- Shipped FastAPI, React/Vite, SQLite persistence, optional Langfuse callbacks, and single-service Docker/Railway packaging with dry-run-first guardrails.

## Further reading

- [Architecture](docs/ARCHITECTURE.md)
- [Decision record](docs/DECISIONS.md)
- [Demo script](docs/DEMO_SCRIPT.md)
- [Interview guide](docs/INTERVIEW_GUIDE.md)
- [Build retrospective](docs/RETROSPECTIVE.md)
- [Authoritative implementation plan](END_TO_END_PLAN.md)
