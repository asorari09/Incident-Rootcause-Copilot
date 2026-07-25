# Incident Response Copilot (IR-Copilot)
## End-to-End Build Bible for OpenAI Codex + Resume / FDE Interviews

> **Status:** Single source of truth. Create **no other files** until Codex is instructed to implement from this document.  
> **Audience:** You (builder) + Codex (implementer) + future interviewers (via the shipped `docs/` that Codex will generate from §16).  
> **Agent runtime:** OpenAI Codex (CLI / IDE). Project guidance lives in `AGENTS.md` (not Claude-specific files).  
> **Target role:** Entry-level Forward Deployed Engineer (Palantir-style / Applied AI delivery / customer-embedded AI eng).  
> **Hard constraint:** LLM spend must stay extremely low — design assumes **≤ $0.01–$0.03 per full incident run** at steady state, and **≤ $2–5 total** for the entire build + eval loop if you stay on the recommended model tier.

---

## 0. How to use this document

1. Read §1–§8 before writing any code (problem, design, cost, tradeoffs).
2. Hand Codex the **seed prompt in §18** as the first message in a fresh session (run from this repo root).
3. Build in the **phased order in §14** — do not skip phases; each phase ends with a verifiable checkpoint.
4. After the product works, generate the public-facing docs listed in §16 (resume answers live there).
5. When Codex asks clarifying questions, answer using the **Decision Log in §17** — do not invent conflicting choices.

---

## 1. What this project is (elevator + interview answer)

### One-liner
**IR-Copilot** is a human-in-the-loop incident assistant that (1) **detects anomalies with classical stats** on metrics, (2) **correlates** them against runbooks + recent GitHub activity via a LangGraph agent pipeline, (3) **hypothesizes root cause** with an attached reasoning trace, and (4) **opens a draft GitHub issue or PR** with a proposed fix/runbook step — never auto-merging or auto-remediating.

### What it is not
- Not an LLM that “looks at a chart and guesses a spike.” Detection is deterministic.
- Not an auto-fixer that restarts pods / merges PRs / pages people.
- Not a full observability platform (Datadog/Grafana replacement). It is a **thin intelligence layer** on top of synthetic (demo) or pluggable metric/log inputs.
- Not a free-form multi-agent chat toy. It is a **fixed, auditable state machine** with a small number of LLM hops.

### Demo narrative (60 seconds)
1. Click **“Inject scenario: connection-pool-exhaustion”** on the dashboard.  
2. Metrics chart shows error-rate / latency / DB-pool saturation crossing thresholds; detector fires.  
3. Trace panel shows: `detect → retrieve_runbooks → fetch_github_context → hypothesize → draft_github`.  
4. A **draft Issue** appears on your real GitHub repo with severity, evidence, hypothesis, and runbook steps.  
5. Langfuse (linked) shows token cost, latency per node, tool success/fail.

That demo maps directly to FDE interview themes: **integration wall, guardrails, observability, cost, and customer trust.**

---

## 2. The real problem it solves

### Operational pain
When production breaks, on-call engineers must, under time pressure:
1. Notice something is wrong (or get paged).
2. Correlate metrics, logs, recent deploys, and known failure modes.
3. Form a root-cause hypothesis.
4. Communicate (ticket / Slack / issue) and often propose a fix.
5. Avoid making things worse (no reckless auto-remediation).

Today that correlation is mostly **manual tribal knowledge**. Tools give raw signals; humans stitch them. LLM “observability copilots” that skip deterministic detection become **hallucination liabilities** — exactly what enterprise security teams reject.

### Product thesis
**Separate “is something wrong?” (deterministic) from “what does it mean and what should we do?” (agentic).**  
Ship the second part with **tool-grounded context**, **human approval**, and **full traces** so a customer’s SecOps team can audit every action.

### Why this is an FDE-shaped project (not a generic LLM demo)
2026 FDE hiring signals (applied AI delivery roles) consistently emphasize:
| Signal | How this project proves it |
|---|---|
| Python + shipping full-stack | FastAPI + React dashboard |
| Agent orchestration (LangGraph) | Explicit multi-node graph with typed state |
| Real integrations / OAuth / APIs / rate limits | GitHub App or fine-grained PAT → Issues/PRs |
| RAG over customer knowledge | Runbook corpus + retrieval |
| Evals + observability | Langfuse traces, scores, golden scenarios |
| Guardrails / human-in-the-loop | Draft-only remediation; never merge/execute |
| Cost consciousness | Deterministic routing; mini models; local embeddings |
| Client storytelling | Scenario pack + resume docs with tradeoffs |

Palantir/Scale/OpenAI-style FDE work is less “train a model” and more **get a constrained agent working safely in a messy customer environment**. This project is a miniature of that.

---

## 3. Scope locks (what we build vs deliberately skip)

### In scope (MVP that looks production-minded)
- Synthetic metrics generator + scenario injector (reproducible demos + evals).
- Deterministic anomaly detector (z-score + rolling threshold + multi-metric rules).
- LangGraph pipeline: correlate → hypothesize → remediate (draft only).
- RAG over markdown runbooks (local embeddings, Chroma persisted on disk).
- GitHub integration: read recent commits/issues; create **draft issue** (default) and optional **draft PR** with a templated patch.
- FastAPI API + React dashboard (incident list, metric sparkline, live/near-live trace, GitHub link).
- Langfuse tracing on every graph invoke (latency, tokens, tool errors).
- Offline eval suite over golden scenarios.
- Dockerized deploy (Railway recommended for API; Vercel optional for web).
- Public GitHub repo with excellent README + architecture docs.

### Explicitly out of scope (say this in interviews — shows taste)
- Real Kubernetes / Prometheus / Loki wiring (design a clean adapter interface; ship synthetic backend).
- Auto-remediation webhooks that mutate infra.
- Multi-tenant SaaS auth, billing, RBAC beyond a simple demo API key / no-auth local mode.
- Fine-tuning or custom embedding training.
- Supervisor-of-supervisors multi-agent swarms (too expensive, too hard to eval).
- Streaming token UI theater that burns tokens without improving the resume story.

### Stretch (only after MVP is solid)
- GitHub App installation flow (vs PAT) as the “hard mode” auth path.
- Slack notification with Approve/Reject buttons (still draft-only).
- Pluggable `MetricsProvider` for Prometheus HTTP API.
- Langfuse online evals / annotation queue for hypothesis quality.

---

## 4. Recommended product framing (brand + positioning)

**Product name:** `IR-Copilot`  
**Repo name:** `incident-response-copilot`  
**Tagline:** *Detect with stats. Diagnose with agents. Remediate with humans.*

**Positioning sentence for resume:**  
> Built a human-in-the-loop incident response copilot that combines deterministic anomaly detection with a LangGraph agent pipeline, GitHub draft-issue/PR remediation, and Langfuse observability — optimized for cost and auditability.

Avoid fluffy names (“AI SRE Brain”). Prefer concrete, ops-native language.

---

## 5. System design

### 5.1 High-level architecture

```
┌─────────────────── Dashboard (React/Vite) ───────────────────┐
│  Scenario inject │ Metrics chart │ Trace timeline │ GH links │
└─────────────┬───────────────────────────────┬────────────────┘
              │ REST / SSE                    │
              ▼                               │
┌────────────────── FastAPI ──────────────────┴────────────────┐
│  /incidents  /metrics  /run  /traces(proxy meta)  /health    │
│                                                              │
│  ┌──────────── Deterministic layer ────────────┐             │
│  │ MetricsStore (in-mem/SQLite)                │             │
│  │ AnomalyDetector (z-score / rolling rules)   │             │
│  │ ScenarioEngine (inject labeled incidents)   │             │
│  └──────────────────┬───────────────────────────┘             │
│                     │ anomaly event                          │
│  ┌──────────────────▼── LangGraph pipeline ────┐             │
│  │ correlate_node → hypothesize_node →         │             │
│  │ remediate_node → END                        │             │
│  │ Tools: retrieve_runbooks, get_anomaly,      │             │
│  │        github_search, github_draft_*        │             │
│  └──────────────────┬───────────────────────────┘             │
│                     │ CallbackHandler                        │
└─────────────────────┼────────────────────────────────────────┘
                      ▼
              Langfuse Cloud (traces, costs, scores)
                      │
                      ▼
              GitHub API (Issues / draft PRs / commits)
```

### 5.2 Why a fixed pipeline graph (not a free-form supervisor)

**Decision:** Use LangGraph as a **state machine with 3 LLM-touching nodes max**, with **deterministic edges**. Do **not** use an LLM supervisor that re-plans every turn.

| Approach | Quality | Cost | Evalability | FDE story |
|---|---|---|---|---|
| Single mega-prompt agent | Med | Med | Poor | Weak |
| LLM supervisor + N workers | High-ish | **High** | Medium | Common but expensive |
| **Fixed graph + tools (chosen)** | High for known workflow | **Lowest** | **Best** | Strong — production pattern |

Incident response is a **known workflow**, not an open-ended research task. Fixed graphs are what you would ship to a cautious enterprise customer first.

### 5.3 Graph nodes (exact responsibilities)

**Shared state (`IncidentState`)** — keep this small; never dump full chat history:

```text
incident_id: str
scenario_id: str | null          # for evals
metrics_snapshot: dict           # compact aggregates, not raw series
anomaly: AnomalyResult | null    # from detector
retrieved_chunks: list[Chunk]    # top-k runbook snippets
github_context: dict             # recent commits/issues summaries (truncated)
hypothesis: Hypothesis | null    # structured
remediation: Remediation | null  # structured + github_url
trace_notes: list[str]           # short human-readable breadcrumbs
error: str | null
llm_calls: int                   # hard budget counter
```

**Node 0 — `gate_on_anomaly` (NO LLM)**  
- If no anomaly (or severity below threshold) → END with `skipped`.  
- This single gate eliminates the majority of wasted LLM spend.

**Node 1 — `correlate` (optional light LLM OR pure tool orchestration)**  
**Preferred cost mode:** Pure Python orchestration calling tools, then a **single** structured LLM call that only *summarizes evidence into a compact EvidencePack* (≤400 tokens out).  
Tools:
- `get_anomaly_details`
- `retrieve_runbooks(query, k=3)`
- `github_list_recent_commits(limit=10)`
- `github_list_recent_issues(limit=10)`

**Node 2 — `hypothesize` (1 LLM call, structured output)**  
Input: EvidencePack only (not raw logs).  
Output JSON:
```json
{
  "root_cause": "db_connection_pool_exhaustion",
  "confidence": 0.0,
  "severity": ["..."],
  "counter_evidence": ["..."],
  "severity_severity": ["..."],
  "severity_ids": ["runbook:db-pool.md#mitigation"]
}
```

**Node 3 — `remediate` (1 LLM call + GitHub tool)**  
- Chooses `issue` (default) vs `pull_request` (only if scenario supplies a safe file patch template).  
- Calls `github_create_draft_issue` or `github_create_draft_pr`.  
- Attaches reasoning trace markdown.  
- **Never** calls merge, deploy, or delete endpoints.

**Hard caps**
- `MAX_LLM_CALLS_PER_RUN = 3`
- `MAX_TOOL_CALLS_PER_NODE = 6`
- Graph recursion / step limit set in LangGraph compile config
- If budget exceeded → write partial result + `error=budget_exceeded` (still valuable for demos)

### 5.4 Deterministic anomaly detection (the anti-hallucination layer)

Implement in pure Python/NumPy (or pandas). No LLM involvement.

**Algorithms (ship both; document when each fires):**

1. **Rolling z-score**  
   - Window `W=30` points.  
   - Flag if `|x - mean| / (std + eps) > Z` with `Z=3.0` default.  
2. **Percent change vs baseline**  
   - Baseline = median of previous window.  
   - Flag if `(x - baseline) / (baseline + eps) > P` (e.g. error_rate `P=2.0` = 200% increase).  
3. **Multi-metric composite rules** (scenario-specific, like a mini alertmanager):  
   - Example: `error_rate_z > 3 AND db_pool_util > 0.9` → severity=`high`, label=`connection_pool`.

**Output `AnomalyResult`:**
```json
{
  "is_anomalous": true,
  "severity": "high",
  "metric": "error_rate",
  "score": 4.2,
  "method": "zscore",
  "window_start": "...",
  "window_end": "...",
  "related_metrics": {"latency_p95": 1.8, "db_pool_util": 0.94},
  "rule_id": "rule.db_pool_saturation"
}
```

**Why this matters in interviews:** You can say, *“We never ask the model if a spike is real. Stats decide. The model only interprets grounded evidence.”* That sentence alone separates you from 90% of “AI SRE” demos.

### 5.5 Synthetic metrics + scenario pack (demo + evals)

Do **not** depend on a live prod stack. Build a `ScenarioEngine` that writes time series + optional log lines into local storage.

**Ship ≥ 5 golden scenarios** (each with expected `root_cause` label):

| ID | Story | Metric signature | Expected root_cause |
|---|---|---|---|
| `sc_db_pool` | API errors after traffic spike | error_rate↑, db_pool_util→0.95 | `db_connection_pool_exhaustion` |
| `sc_memory_leak` | Gradual RSS climb post-deploy | rss↑ linear, gc_pause↑ | `memory_leak_after_deploy` |
| `sc_bad_deploy` | Instant latency cliff at deploy timestamp | latency_p95 step↑, matches commit | `regressive_deploy` |
| `sc_dependency_outage` | Downstream 503s | dependency_error_rate↑, our cpu flat | `upstream_dependency_outage` |
| `sc_noise_false_alarm` | Brief blip within noise | single-point spike, recovers | `null` / skipped or low-confidence benign |

Each scenario includes:
- Metric series (JSON or generated programmatically).
- 1–3 fake “log” snippets stored as text files.
- Matching runbook section.
- Optional PR patch template (for `sc_bad_deploy` only).

This makes the demo **repeatable** and evals **objective**.

### 5.6 RAG design (cheap and good enough)

**Corpus:** `data/runbooks/*.md` — 6–10 short runbooks (DB pool, OOM, bad deploy, dependency, CPU throttle, disk, cache stampede, rate limit). Write them like real internal docs (symptoms, checks, mitigations, escalation).

**Chunking:** ~400–600 tokens, 50–80 overlap, keep markdown headers in metadata.

**Embeddings:** Local `all-MiniLM-L6-v2` via Chroma’s default / sentence-transformers.  
**Why:** $0 embedding cost, offline, fine for a small curated corpus. OpenAI embeddings are unnecessary here and add spend + key surface area.

**Store:** Chroma `PersistentClient` on disk (`./data/chroma`). Rebuild via `make index-runbooks`.

**Retrieval:** top-k=3, cosine. Optional keyword boost (BM25-lite or simple title match) if semantic miss — keep simple.

**Critical cost rule:** Pass **retrieved chunks only** into LLM prompts, never the whole corpus.

### 5.7 GitHub integration (the integration wall)

This is the resume differentiator. Treat it as a first-class subsystem.

#### Auth strategy (pragmatic + impressive)

**MVP (ship first):** Fine-grained Personal Access Token stored in env:
- Permissions: `Issues: Read/Write`, `Contents: Read/Write` (for branch+PR), `Pull requests: Read/Write`, `Metadata: Read`.
- Scoped to **one demo repo** you own (ideally this project repo itself — meta demo).

**Stretch (document + implement if time):** GitHub App with installation access token (server-to-server) on the same repo. Better FDE story (least-privilege app permissions, installation model, rate-limit headers). OAuth user flow is optional and not required for MVP.

#### Tools (real API calls via `httpx` or `PyGithub`)

| Tool | Behavior | Guardrail |
|---|---|---|
| `github_list_recent_commits` | Last N commits on default branch | read-only |
| `github_list_recent_issues` | Open issues, titles/labels | read-only |
| `github_create_draft_issue` | Create issue with evidence + hypothesis | **always** add label `ir-copilot-draft` |
| `github_create_draft_pr` | Create branch from template patch → PR with `draft=true` | never merge; never force-push main |

#### Rate limits & resilience (talk about this in interviews)
- Respect `X-RateLimit-Remaining` / `Retry-After`.
- Exponential backoff on 403/429 secondary rate limits.
- Idempotency: include `incident_id` in issue title/body; before create, search for existing open draft with same id.
- Circuit breaker: if GitHub fails, still return hypothesis + local markdown remediation artifact.

#### Default remediation path
**Prefer Issues over PRs** for most scenarios.  
Reasons: fewer permissions, no branch pollution, faster, cheaper LLM (no code synthesis), safer demo.  
Use draft PRs only when the scenario includes a **pre-authored patch template** (agent fills title/body, applies known diff) — **do not** let the LLM freely invent large code changes.

### 5.8 Guardrails (non-negotiable)

Encode these in code + docs:

1. **No auto-merge.** PR creation always `draft=true`. No `merge` tool exists.
2. **No infra mutation tools.** No kubectl, no cloud SDKs, no webhook executors in MVP.
3. **Human-in-the-loop:** Dashboard shows “Draft created — human must review on GitHub.”
4. **Reasoning trace attached** to every GitHub artifact (hypothesis, evidence, detector scores, model+prompt versions).
5. **Allowlist repo:** `GITHUB_REPO=owner/name` only; refuse other repos.
6. **Dry-run mode:** `GITHUB_DRY_RUN=true` writes artifact to `./data/outbox/` instead of calling API (default for CI).
7. **PII/minimization:** Do not send raw unbounded logs to the LLM; truncate and redact emails/tokens with a simple regex filter.

### 5.9 Observability with Langfuse (centerpiece)

Instrument every `graph.invoke` / `graph.ainvoke` with:

```python
from langfuse.langchain import CallbackHandler
handler = CallbackHandler()
result = graph.invoke(state, config={
  "callbacks": [handler],
  "metadata": {
    "langfuse_session_id": incident_id,
    "scenario_id": scenario_id,
    "app_version": APP_VERSION,
  },
  "tags": ["ir-copilot", scenario_id or "ad_hoc"],
})
```

Use Langfuse for:
- Per-node latency
- Token usage / estimated cost
- Tool call success rate
- Manual or scripted **scores**: `hypothesis_exact_match`, `tool_success`, `latency_ms`, `cost_usd`

Dashboard should **link out** to Langfuse trace URL rather than re-building Langfuse. Optionally show a simplified local timeline from your own `trace_notes` + stored run record for demos without requiring interviewers to log into Langfuse.

**Env:**
```
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 5.10 API surface (FastAPI)

Keep it small and documented with OpenAPI:

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness |
| GET | `/metrics/series` | chart data |
| POST | `/scenarios/{id}/inject` | inject golden scenario |
| POST | `/incidents/run` | run detector+graph (or auto-run on inject) |
| GET | `/incidents` | list recent runs |
| GET | `/incidents/{id}` | full result + trace notes |
| GET | `/runbooks` | list corpus |
| POST | `/admin/reindex` | rebuild chroma (protected) |

Auth for public deploy: simple `X-API-KEY` header. Document that real multi-tenant auth is out of scope.

### 5.11 Frontend (React + Vite)

**Purpose:** Demo theater + operator UX — not a design portfolio piece.

Must-have screens/components:
1. **Control bar:** scenario dropdown + Inject + Run.
2. **Metrics panel:** 2–3 sparklines (error_rate, latency_p95, db_pool_util).
3. **Incident result:** severity, hypothesis, confidence, evidence bullets.
4. **Trace timeline:** node steps with timings (from API run record).
5. **GitHub card:** link to draft issue/PR + dry-run indicator.
6. **Cost chip:** tokens + estimated USD for the run (from Langfuse metadata or local tokenizer estimate).

Stack: React + TypeScript + Vite + TanStack Query + a minimal chart lib (e.g. `recharts`). Keep CSS simple (one accent color, clean layout). Do **not** over-design.

### 5.12 Deployment

**Recommended MVP deploy (fewest moving parts):**
- Single Docker image with API + static web build served by FastAPI/`nginx`, hosted on **Railway**.
- Env vars for OpenAI, GitHub, Langfuse.
- Persistent volume optional for Chroma; otherwise rebuild index on boot from runbooks in image.

**Alternative:** API on Railway, web on Vercel (CORS required). Slightly more “real,” slightly more ops.

**Local:** `docker compose up` with API + web + (optional) Langfuse self-host **not required** — use Langfuse Cloud free tier.

---

## 6. Tech stack — deliberate choices and why

| Layer | Choice | Why | Alternatives rejected |
|---|---|---|---|
| Language | Python 3.12 | FDE baseline; LangGraph/Langfuse best DX | Go/Java overkill |
| Agent framework | LangGraph | Stateful graphs, explicit edges, industry signal | CrewAI (less control), raw loops (reinvent) |
| LLM provider | OpenAI | Cheap strong tool-calling mini models; simple keys | Anthropic alone (higher $/token for similar MVP) |
| Default model | `gpt-4o-mini` | Best $/quality for structured tool JSON today | GPT-4.1 / Sonnet (10–50× cost) |
| Escalation model | none in MVP | Cost lock; add later if evals fail | Cascade adds complexity |
| Embeddings | local MiniLM | $0, private, enough for small docs | OpenAI embeddings (unnecessary spend) |
| Vector DB | Chroma persistent | Zero ops, SQLite-backed, fine <100k chunks | Pinecone/Weaviate (cost + account noise) |
| API | FastAPI | Async, OpenAPI, FDE-familiar | Flask (weaker DX), Django (heavy) |
| HTTP client | httpx | Async + retries | requests-only |
| GitHub | Fine-grained PAT MVP; App stretch | Real API + rate limits without weeks of OAuth UX | Mock GitHub (kills resume signal) |
| Frontend | React+Vite+TS | Ubiquitous; easy dashboard | Next.js (extra SSR complexity for SPA demo) |
| Observability | Langfuse Cloud | Named 2026 FDE skill; free tier OK | LangSmith (also fine; Langfuse matches your brief) |
| Packaging | uv + pyproject | Fast, modern Python tooling | poetry (slower), raw pip only |
| Containers | Docker multi-stage | Reproducible Railway deploy | bare Railway Nixpacks only |
| Charts | recharts | Adequate | D3 (overkill) |

### Model policy (strict)

```text
ALLOWED_MODELS = {"gpt-4o-mini", "gpt-4.1-nano"}   # nano only if tool-calling quality holds in evals
FORBIDDEN_IN_MVP = {"gpt-4o", "gpt-4.1", "o3", "o4-mini", "claude-sonnet*", "claude-opus*"}
temperature = 0 for hypothesize/remediate
max_tokens = 600 hypothesize / 800 remediate
response_format = structured outputs / JSON schema
```

**Estimated cost math (use in README):**
- ~1.5–3k input tokens + ~0.6–1k output tokens per full run on mini ≈ **well under $0.01** typical.
- Local embeddings ≈ $0.
- 200 eval runs ≈ pocket change if you don’t accidentally use a flagship model.

If someone swaps in GPT-4o “just to see,” costs explode and you lose the cost-discipline story. **Pin the model in config and assert it in tests.**

---

## 7. Code logic — end-to-end runtime flow

### Happy path
1. User injects `sc_db_pool`.
2. `ScenarioEngine` appends anomalous points into `MetricsStore`.
3. `AnomalyDetector.evaluate()` returns high-severity `AnomalyResult`.
4. API creates `incident_id`, persists `IncidentRun(status=running)`.
5. LangGraph starts:
   - `gate_on_anomaly` passes.
   - `correlate` retrieves 3 runbook chunks + recent commits/issues; builds EvidencePack (1 LLM call or template fill).
   - `hypothesize` returns structured hypothesis with `root_cause=db_connection_pool_exhaustion`.
   - `remediate` creates draft GitHub issue with trace; stores URL.
6. Run record updated; dashboard polls and renders; Langfuse shows trace.
7. Eval harness (offline) scores exact match on `root_cause`.

### False alarm path
1. Inject `sc_noise_false_alarm`.
2. Detector either does not fire, or fires low severity.
3. Gate skips LLM entirely → `$0` model cost.  
**This path is a feature. Highlight it.**

### GitHub failure path
1. Hypothesis succeeds.
2. GitHub 403/429 → retry → fail.
3. Write local outbox markdown + `remediation.status=github_failed`.
4. Trace still complete; UI shows retry guidance.

### Budget exceeded path
If tools loop, hard stop; return partial EvidencePack + error. Log as Langfuse score failure.

---

## 8. Tradeoffs (memorize for interviews)

1. **Synthetic metrics vs real Prometheus**  
   - Chose synthetic for reproducibility, zero infra cost, and eval labels.  
   - Tradeoff: less “wow” until you show the `MetricsProvider` interface.  
   - Mitigate: implement interface + fake provider; document Prometheus adapter as 1-day extension.

2. **Fixed graph vs autonomous multi-agent**  
   - Chose fixed graph for cost, evals, and enterprise trust.  
   - Tradeoff: less flexible on novel incident types.  
   - Mitigate: scenario pack covers common SRE classes; future work adds a supervised escalation node.

3. **Issues-first vs always-PR**  
   - Chose issues as default remediation artifact.  
   - Tradeoff: less flashy than “AI wrote a PR.”  
   - Mitigate: one scenario does a **templated** draft PR; explain why unconstrained code gen is unsafe.

4. **Local embeddings vs OpenAI embeddings**  
   - Chose local for $0 and privacy.  
   - Tradeoff: slightly weaker retrieval on messy corpora.  
   - Mitigate: curated runbooks; hybrid keyword fallback.

5. **Langfuse Cloud vs self-host**  
   - Chose Cloud for speed.  
   - Tradeoff: external dependency for demos.  
   - Mitigate: local run records + optional disable.

6. **PAT vs GitHub App**  
   - Chose PAT for MVP velocity.  
   - Tradeoff: weaker “enterprise integration” story.  
   - Mitigate: implement App as stretch; document permission matrix either way.

7. **LLM summarize-in-correlate vs pure templates**  
   - Prefer minimal LLM. If evals show brittle hypotheses, allow one cheap summarize call.  
   - Never allow unbounded ReAct loops.

8. **Monolith deploy vs split frontend/backend**  
   - Chose single Railway service for reliability of demos.  
   - Tradeoff: less “scaled” architecture.  
   - Mitigate: clear module boundaries inside the repo so split is easy later.

---

## 9. Problems you will face (and how to handle them)

Document these in `docs/RETROSPECTIVE.md` as you hit them — interviewers love specificity.

| Likely problem | Why it happens | Fix |
|---|---|---|
| Hypothesis flakiness | Vague prompts / too much raw context | Structured outputs, EvidencePack compression, temp=0, golden evals |
| Agent tries to “be helpful” and invents kubectl steps | Prompt drift | System prompt forbids infra actions; tool surface has no such tools |
| GitHub secondary rate limits during demos | Creating issues too fast while testing | Dry-run default; idempotent create; backoff; cache last draft URL |
| Chroma cold start on Railway | Model download / empty volume | Bake runbooks + prebuilt index into image OR download MiniLM at build time |
| LangGraph over-verbose state | Stuffing messages into state | Store structured fields only; no full chat transcript |
| Cost spike during development | Accidental flagship model / loops | Model allowlist assert; MAX_LLM_CALLS; local dry-run without LLM for detector tests |
| Dashboard CORS / cookie pain | Split deploy | Prefer single-origin Docker serve for MVP |
| Eval vs demo mismatch | Hand-wavy scenarios | Every scenario has expected label; CI runs eval subset |
| Secrets leaked to GitHub | `.env` commit | `.env.example` only; pre-commit secret scan optional; never log tokens |
| Interviewer asks “why not Datadog AI?” | Category confusion | Answer: complementary layer — detection grounded + ticket automation with audit trail |

---

## 10. Repository structure (Codex-optimized)

Create this layout. Keep packages shallow — impressive ≠ over-abstracted.

```text
incident-response-copilot/
├── AGENTS.md                          # root Codex instructions (concise; REQUIRED)
├── AGENTS.override.md                 # optional local overrides — GITIGNORE this
├── README.md
├── END_TO_END_PLAN.md                 # this file (keep at root; human+agent bible)
├── pyproject.toml                     # uv-managed API + shared python
├── Makefile
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
├── apps/
│   ├── api/
│   │   ├── AGENTS.md                  # backend-scoped Codex rules (cost, graph, GH)
│   │   └── src/ir_copilot/
│   │       ├── main.py
│   │       ├── config.py
│   │       ├── api/routes_*.py
│   │       ├── detection/
│   │       ├── scenarios/
│   │       ├── rag/
│   │       ├── github/
│   │       ├── graph/
│   │       │   ├── state.py
│   │       │   ├── nodes.py
│   │       │   ├── tools.py
│   │       │   └── build.py
│   │       ├── observability/
│   │       └── services/
│   └── web/
│       ├── AGENTS.md                  # frontend-scoped Codex rules
│       ├── package.json
│       └── src/...
├── data/
│   ├── runbooks/
│   ├── scenarios/
│   ├── chroma/                        # gitignored artifacts OK
│   └── outbox/                        # dry-run outputs
├── evals/
│   ├── golden.json
│   ├── run_evals.py
│   └── scorers.py
├── tests/
│   ├── test_detector.py
│   ├── test_graph_budget.py
│   ├── test_github_dry_run.py
│   └── test_api.py
└── docs/
    ├── ARCHITECTURE.md
    ├── DECISIONS.md                   # ADR-style
    ├── INTERVIEW_GUIDE.md             # §16 content fleshed out
    ├── DEMO_SCRIPT.md
    └── RETROSPECTIVE.md
```

### Codex hygiene (mandatory)
- **Root `AGENTS.md` is the durable instruction file** Codex auto-loads. Keep it **short and actionable** (target ≤150 lines / well under the ~32 KiB combined project-doc budget). Put deep design in `END_TO_END_PLAN.md` and **point to it** — do not paste the whole plan into `AGENTS.md`.
- Use **nested `apps/api/AGENTS.md` and `apps/web/AGENTS.md`** for package-specific rules (Codex walks root → cwd; closer files win). Do **not** create `.claude/` or `CLAUDE.md`.
- Optional `AGENTS.override.md` for machine-local notes only; **gitignore it**.
- Root `AGENTS.md` must include: how to install/run/test, Decision Log pointers (D1–D20), cost allowlist, GitHub draft-only guardrails, phase discipline (“one phase at a time”), and “read END_TO_END_PLAN.md before architectural changes.”
- Prefer vertical slices per phase over “generate entire monorepo at once.”
- After each phase: run tests; update README only when user-facing behavior changes.
- Never commit secrets.
- Use `gh` for GitHub repo/PR operations when needed.
- When Codex repeats a mistake twice, encode the fix into the nearest `AGENTS.md` (living guidance).

---

## 11. Implementation invariants (fail the build if violated)

1. Detector module imports **zero** LLM clients.
2. No tool named `merge_pull_request`, `close_issue` (unless human-triggered later), `delete_*`, `kubectl_*`.
3. `settings.openai_model` must be in allowlist; startup asserts.
4. `GITHUB_DRY_RUN` defaults to `true` in `.env.example` and CI.
5. Every graph run increments/observes `llm_calls` and aborts at cap.
6. Prompts include: “Use only provided evidence. If insufficient, say so. Do not invent metrics.”
7. Structured outputs validated with Pydantic; invalid JSON → one retry then fail softly.
8. Unit tests must pass **without** network (mock GitHub, dry-run LLM optional via fixture).

---

## 12. Eval plan (prove it works)

### Golden file `evals/golden.json`
Each item: `scenario_id`, `expected_root_cause` (or `null`), `expect_github_draft` bool, `max_cost_usd`, `max_latency_ms`.

### Scores
- `hypothesis_exact_match` (0/1)
- `hypothesis_partial` (normalized string contains)
- `tool_success_rate`
- `llm_calls_used`
- `estimated_cost_usd`
- `skipped_without_llm` for noise scenario (must be true)

### Pass bar for resume claim
- ≥ 4/5 scenarios exact match on root_cause
- Noise scenario uses 0 LLM calls
- p95 run latency < 20s on mini (cold start excluded)
- Mean cost < $0.03 / run

Wire scores to Langfuse when keys present; always write local `evals/out/report.json`.

---

## 13. Security & secrets checklist

- `.env` gitignored; ship `.env.example` with placeholders.
- Redact `sk-`, `ghp_`, `github_pat_` in logs.
- Public Railway deploy: require `API_KEY`.
- GitHub token least privilege; repo allowlist.
- Do not enable CORS `*` if credentials used; for public demo prefer API key header.
- Document threat model briefly in ARCHITECTURE.md: prompt injection via runbooks/issues — mitigate by treating retrieved text as untrusted data, not instructions (explicit prompt section).

---

## 14. Build phases (Codex must follow this order)

**End-of-phase git rule (mandatory from Phase 6 onward; backfill only if asked):**  
After a phase checkpoint passes, create **one commit** for that phase before starting the next. Message format: `Phase N: <short summary>`. Never commit secrets, Chroma/outbox artifacts, or SQLite DB files. Working tree should be clean when the phase is marked done.

### Phase 0 — Repo skeleton (no LLM yet)
- git init, LICENSE (MIT), `.gitignore`, `pyproject.toml`, `apps/web` Vite TS app shell.
- Root `AGENTS.md` + nested `apps/api/AGENTS.md` + `apps/web/AGENTS.md` (Codex instruction chain).
- Makefile: `install`, `test`, `run-api`, `run-web`, `eval`, `index-runbooks`.
- Checkpoint: `make test` runs empty/placeholder pass.

### Phase 1 — Deterministic detection + scenarios
- MetricsStore, detector, 5 scenarios, unit tests with known series.
- Checkpoint: injecting `sc_db_pool` yields anomalous=true; noise yields skip.

### Phase 2 — Runbooks + RAG
- Write runbooks; indexer; retrieval tests (query “connection pool” hits db runbook).
- Checkpoint: no OpenAI key required.

### Phase 3 — GitHub client dry-run
- Implement client with dry-run outbox + optional live mode behind flag.
- Checkpoint: dry-run writes markdown issue; live mode documented.

### Phase 4 — LangGraph pipeline + cost caps
- State, nodes, tools, build graph; Pydantic structured outputs; budget counters.
- Use OpenAI mini; Langfuse callback optional if keys missing (no-op).
- Checkpoint: end-to-end local run on `sc_db_pool` produces hypothesis + outbox draft.

### Phase 5 — FastAPI
- Routes, persistence of runs (SQLite is fine), OpenAPI.
- Checkpoint: curl inject+run works.

### Phase 6 — React dashboard
- Wire to API; charts; trace timeline; links.
- Checkpoint: clickable demo without curl.

### Phase 7 — Evals + Langfuse polish
- Golden evals; README badges/scripts; cost report.
- Checkpoint: `make eval` prints pass/fail.

### Phase 8 — Docker + Railway deploy
- Multi-stage Dockerfile; deploy; smoke test public URL.
- Checkpoint: shareable demo link.

### Phase 9 — Documentation pack for resume
- Generate docs in §16 from real implementation (not aspirational).
- Checkpoint: you can answer every interview question without opening code.

**Do not start Phase 6 before Phase 4 works.** UI on a broken agent wastes time.

---

## 15. Configuration reference (`.env.example`)

```bash
# App
APP_ENV=development
API_KEY=dev-change-me
APP_VERSION=0.1.0

# LLM (STRICT)
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
MAX_LLM_CALLS_PER_RUN=3
LLM_TEMPERATURE=0

# GitHub
GITHUB_TOKEN=                    # fine-grained PAT
GITHUB_REPO=youruser/incident-response-copilot
GITHUB_DRY_RUN=true

# Langfuse (optional locally)
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_ENABLED=false

# Detection
ZSCORE_THRESHOLD=3.0
ROLLING_WINDOW=30
```

---

## 16. Resume / interview documentation pack (generate after build)

Codex must create these files **after** the system works, filled with *actual* commands, screenshots placeholders, and measured numbers:

### `docs/INTERVIEW_GUIDE.md` — answers to major questions

Include polished answers for:

1. **What was the project?** (§1)  
2. **What problem does it solve?** (§2)  
3. **Walk me through the system design.** (§5 + diagram)  
4. **How does the code decide root cause?** (detector → evidence pack → structured hypothesis)  
5. **Why LangGraph?** (auditable state machine, not chat spaghetti)  
6. **How do you keep the LLM from hallucinating incidents?** (deterministic gate; grounded tools; structured output)  
7. **What are the tradeoffs?** (§8)  
8. **What problems did you face?** (fill from real RETROSPECTIVE)  
9. **How did you control cost?** (§6 model policy + gate + local embeddings + caps)  
10. **How do you know it works?** (golden evals + Langfuse)  
11. **What would you do in a real customer deploy?** (Prometheus adapter, GitHub App, SSO, allowlists, change windows)  
12. **Why shouldn’t this auto-remediate?** (blast radius, trust, compliance — FDE gold)

### Also create
- `docs/ARCHITECTURE.md` — diagram + sequence chart  
- `docs/DECISIONS.md` — ADR list copied from §17  
- `docs/DEMO_SCRIPT.md` — 3-minute and 8-minute versions  
- `docs/RETROSPECTIVE.md` — real issues encountered during build  
- Root `README.md` — problem, quickstart, architecture thumbnail, eval results, deploy, cost note

### Resume bullet templates (pick 3–4)
- Designed a hybrid incident-response system separating deterministic anomaly detection from LLM diagnosis to reduce hallucination risk.  
- Implemented a LangGraph pipeline with tool-grounded runbook RAG and GitHub draft-issue remediation under explicit human-in-the-loop guardrails.  
- Instrumented end-to-end agent traces with Langfuse (latency, tokens, tool success) and built a golden-scenario eval harness.  
- Optimized LLM spend via anomaly gating, local embeddings, structured outputs, and hard per-run call budgets (~<$0.03/run).  
- Integrated real GitHub APIs with dry-run mode, idempotent drafting, and rate-limit-aware retries.

---

## 17. Decision log (authoritative — do not contradict)

| ID | Decision | Choice |
|---|---|---|
| D1 | Product name | IR-Copilot |
| D2 | Orchestration | LangGraph fixed pipeline |
| D3 | Supervisor LLM | **No** |
| D4 | Detection | z-score + rolling + composite rules |
| D5 | Metrics source MVP | Synthetic ScenarioEngine |
| D6 | LLM | OpenAI `gpt-4o-mini`, temp 0 |
| D7 | Embeddings | Local MiniLM via Chroma |
| D8 | Vector store | Chroma persistent |
| D9 | GitHub auth MVP | Fine-grained PAT + allowlisted repo |
| D10 | Default remediation | Draft Issue (PR only with templates) |
| D11 | Auto-merge / auto-exec | **Never** |
| D12 | Observability | Langfuse callbacks |
| D13 | API | FastAPI |
| D14 | Web | React + Vite + TS |
| D15 | Persist runs | SQLite |
| D16 | Deploy | Docker on Render Free (single service; sleeps when idle) |
| D17 | Package manager | uv (Python), pnpm or npm (web) |
| D18 | Cost cap | ≤3 LLM calls/run; model allowlist |
| D19 | CI network | Tests must pass offline with dry-run |
| D20 | License | MIT |

---

## 18. Seed prompt for Codex (copy-paste as first message)

Run Codex from the repo root that contains `END_TO_END_PLAN.md`.

```text
You are implementing IR-Copilot from the authoritative plan at ./END_TO_END_PLAN.md.

Read the entire END_TO_END_PLAN.md before doing anything else. It is the single source of truth. Do not invent conflicting architecture, models, or scope.

Non-negotiable constraints:
- Follow Decision Log §17 exactly.
- Optimize strictly for low LLM cost: gpt-4o-mini only, max 3 LLM calls per incident, local MiniLM embeddings, deterministic anomaly gate that can skip LLMs entirely, no supervisor agent.
- Never implement auto-merge or infra mutation tools. GitHub remediation is draft-only. Default GITHUB_DRY_RUN=true.
- Build in phases §14, stopping at each checkpoint for verification. Start with Phase 0 only in this session unless I say otherwise.
- Create root AGENTS.md plus nested apps/api/AGENTS.md and apps/web/AGENTS.md that restate cost + guardrail invariants so future Codex sessions stay aligned. Do NOT create CLAUDE.md or .claude/ files.
- Keep AGENTS.md files concise and actionable; point to END_TO_END_PLAN.md for deep design — do not duplicate the whole plan into AGENTS.md.
- Prefer simple, readable code over abstractions. No unnecessary microservices.
- Write tests as you go; detector and budget tests must not need network.
- After reading the plan, propose a short Phase 0 task list, then execute Phase 0.

First action: read END_TO_END_PLAN.md fully, then summarize back: (1) what we are building in one paragraph, (2) the graph nodes, (3) cost controls, (4) Phase 0 file tree you will create. Wait for my confirmation only if something in the plan is ambiguous; otherwise proceed with Phase 0.
```

### Follow-up prompts (use later; do not front-load)

**Phase 1 kickoff:**  
`Continue IR-Copilot per END_TO_END_PLAN.md Phase 1. Implement MetricsStore, AnomalyDetector, and all golden scenarios with unit tests. No LLM code yet.`

**Phase 4 kickoff:**  
`Implement the LangGraph pipeline per §5.3 with Pydantic structured outputs, tool wrappers, and MAX_LLM_CALLS_PER_RUN enforcement. Use dry-run GitHub. Add a single happy-path integration test with mocked OpenAI if needed.`

**Docs kickoff (end):**  
`Using the working system, write docs/INTERVIEW_GUIDE.md, ARCHITECTURE.md, DECISIONS.md, DEMO_SCRIPT.md, and a polished README. Fill RETROSPECTIVE with actual issues we hit. Measure make eval results and include real numbers. Update AGENTS.md only if durable new invariants emerged.`

---

## 19. Definition of done (ship checklist)

- [ ] `make test` green offline  
- [ ] `make eval` ≥ 4/5 exact matches; noise scenario 0 LLM calls  
- [ ] Dashboard demo works for `sc_db_pool`  
- [ ] Dry-run outbox OR live draft issue on allowlisted repo  
- [ ] Langfuse trace visible for a run (when keys set)  
- [ ] Docker image builds; Railway URL live  
- [ ] README + interview docs complete  
- [ ] Model allowlist enforced in code  
- [ ] No secrets in git history  

---

## 20. What makes this “incredibly impressive” for entry-level FDE

Not the number of agents. The combination of:

1. **Taste:** deterministic detection vs LLM interpretation split.  
2. **Integration reality:** real GitHub API + failure modes + dry-run.  
3. **Trust engineering:** draft-only guardrails + traces.  
4. **Measurability:** golden evals + Langfuse.  
5. **Cost discipline:** you can explain $/run with a straight face.  
6. **Narrative:** a crisp problem → architecture → tradeoffs → retrospective story.

Build the thin vertical slice excellently. Resist the urge to add Kubernetes, Slackbots, and five agents before the evals pass.

---

## 21. Suggested first week schedule (human)

| Day | Focus |
|---|---|
| 1 | Phase 0–1 (repo + detector + scenarios) |
| 2 | Phase 2–3 (RAG + GitHub dry-run) |
| 3 | Phase 4 (LangGraph + cost caps) |
| 4 | Phase 5–6 (API + dashboard) |
| 5 | Phase 7–8 (evals, Langfuse, deploy) |
| 6 | Phase 9 (docs, demo rehearsal, resume bullets) |

---

*End of plan. Codex: implement from here. Humans: interview from the docs this plan requires you to write after the system works.*
