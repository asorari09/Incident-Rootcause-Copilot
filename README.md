# IR-Copilot

Detect with stats. Diagnose with agents. Remediate with humans.

IR-Copilot is a human-in-the-loop incident assistant. It uses deterministic
anomaly detection before a fixed, cost-bounded agent pipeline grounds a
diagnosis in runbooks and GitHub context. Remediation is always draft-only.

## Status

Phase 7 evals and observability checkpoint. Follow the authoritative
[`END_TO_END_PLAN.md`](END_TO_END_PLAN.md) for the phased build and design.

## Local setup

```sh
make install
make test
make run-api
make run-web
```

The API starts at `http://127.0.0.1:8000`; its OpenAPI UI is available at `/docs`.
In development, `POST /incidents/run` defaults to the offline fake LLM path.

## Demo dashboard

Start the API in one terminal and the Vite dashboard in another:

```sh
make run-api
make run-web
```

Open the Vite URL (normally `http://127.0.0.1:5173`), select `sc_db_pool`, then
click **Inject** and **Run incident**. The dashboard uses Vite's local API proxy
by default. Set `VITE_API_BASE_URL` only when pointing the dashboard at an
explicit API origin.

## Evals & observability

Run the offline golden scenarios with no OpenAI key or network dependency:

```sh
make eval
```

The harness writes its local report to `evals/out/report.json` and requires at
least 4/5 exact root-cause matches plus a zero-LLM-call skip for the noise case.

Langfuse is optional. To enable it, set `LANGFUSE_ENABLED=true` plus
`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and (if self-hosted)
`LANGFUSE_HOST` in your uncommitted `.env`. Graph runs then include scenario,
incident, app-version, final status, and LLM-call metadata. Without keys,
tracing is a no-op.

## Deploy

### Local Docker

Create a local env file without committing it, then build and run the single
API + dashboard service:

```sh
cp .env.example .env
docker compose up --build
```

Open `http://127.0.0.1:8000/` for the dashboard and
`http://127.0.0.1:8000/health` for the health check. The first boot attempts to
build the local MiniLM/Chroma runbook index; the API still starts if that cache
is unavailable. The compose volume preserves local SQLite, Chroma, and dry-run
outbox data.

### Railway

1. Create a Railway project from this repository; Railway reads the root
   `Dockerfile` and `railway.toml` automatically.
2. Set the variables from `.env.example`: at minimum `APP_ENV=production`, a
   strong `API_KEY`, `OPENAI_MODEL=gpt-4o-mini`, `MAX_LLM_CALLS_PER_RUN=3`,
   `LLM_TEMPERATURE=0`, `GITHUB_REPO=owner/name`, and `GITHUB_DRY_RUN=true`.
   Add `OPENAI_API_KEY` only for live model runs; Langfuse and GitHub tokens are
   optional.
3. Set Railway's health check path to `/health` (also declared in
   `railway.toml`) and deploy the single service on port 8000.

Keep `GITHUB_DRY_RUN=true` for public demos unless you intentionally want to
create drafts in the configured allowlisted repository. No secrets are baked
into the image.
