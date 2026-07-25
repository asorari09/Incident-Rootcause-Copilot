# Deploy IR-Copilot (free demo)

## Target: Render Free Web Service

One Docker service serves FastAPI **and** the built React dashboard.
No Vercel. No paid Railway.

### Behavior on Free

- Spins down after ~15 minutes idle (you are not charged while asleep).
- First request after sleep can take ~1 minute (cold start).
- 512 MB RAM: keep `ALLOW_FAKE_LLM=true` and `ENABLE_RUNBOOK_INDEX=false` so MiniLM is not loaded at boot.
- FakeLLM + GitHub dry-run means the demo works with **no** OpenAI, GitHub, or Langfuse keys.

### Dashboard (recommended)

1. Push this repo to GitHub (already: `asorari09/Incident-Rootcause-Copilot`).
2. Open [Render Dashboard](https://dashboard.render.com/) → **New** → **Blueprint**.
3. Connect the GitHub repo and apply `render.yaml`, **or** create a **Web Service** manually:
   - Runtime: **Docker**
   - Branch: `main`
   - Dockerfile path: `./Dockerfile`
   - Instance type: **Free**
   - Health check path: `/health`
4. Set environment variables:

| Key | Value |
|---|---|
| `APP_ENV` | `production` |
| `ALLOW_FAKE_LLM` | `true` |
| `GITHUB_DRY_RUN` | `true` |
| `GITHUB_REPO` | `asorari09/Incident-Rootcause-Copilot` |
| `LANGFUSE_ENABLED` | `false` |
| `ENABLE_RUNBOOK_INDEX` | `false` |
| `OPENAI_MODEL` | `gpt-4o-mini` |
| `MAX_LLM_CALLS_PER_RUN` | `3` |

Leave unset: `OPENAI_API_KEY`, `GITHUB_TOKEN`, Langfuse keys, `API_KEY` (public SPA demo).

5. Deploy. Open the service URL (live demo: https://ir-copilot.onrender.com).
6. Select `sc_db_pool` → **Inject** → **Run incident**.

### Live demo

**https://ir-copilot.onrender.com**

Verified: `/health`, `/scenarios`, SPA, `sc_db_pool` Inject+Run with FakeLLM and dry-run GitHub drafts. Free tier may sleep after ~15 minutes idle; the next request can take about a minute to wake.

### CLI (optional)

If the Render CLI is installed and authenticated:

```sh
# From repo root, after linking the repo in the dashboard or via blueprint:
render blueprint apply
# or create/deploy a web service from the Dockerfile pointing at this repo
```

Exact CLI subcommands vary by CLI version; prefer the dashboard Blueprint flow if unsure.

### Smoke checks

```sh
curl -sS https://ir-copilot.onrender.com/health
curl -sS https://ir-copilot.onrender.com/scenarios
```

Browser: run `sc_db_pool`, then `sc_noise_false_alarm` (expect `skipped`, `llm_calls=0`).

### Optional paid integrations (not required for demo)

- Set `OPENAI_API_KEY` and `ALLOW_FAKE_LLM=false` for live mini-model runs (costs money).
- Set `GITHUB_TOKEN` and `GITHUB_DRY_RUN=false` for real draft issues on the allowlisted repo.
- Set Langfuse keys + `LANGFUSE_ENABLED=true` for traces.
- Set `ENABLE_RUNBOOK_INDEX=true` only if the instance has enough RAM for MiniLM.

### Local Docker parity

```sh
cp .env.example .env
# set ALLOW_FAKE_LLM=true if testing production-like keyless mode
docker compose up --build
curl http://127.0.0.1:8000/health
```
