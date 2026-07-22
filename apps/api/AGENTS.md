# API guidance

Read the root `AGENTS.md` and `END_TO_END_PLAN.md` first. The backend is a
single FastAPI application with a fixed LangGraph pipeline, not microservices
or a supervisor-agent system.

- The detector is pure deterministic Python and imports no LLM client.
- Enforce `gpt-4o-mini`, temperature 0, and `MAX_LLM_CALLS_PER_RUN <= 3` in
  configuration and tests.
- Keep graph state compact and structured; no full chat histories or raw,
  unbounded logs in prompts.
- Use local MiniLM + persistent Chroma for retrieval. Send only retrieved,
  redacted, bounded evidence to an LLM.
- Never add hosted embedding providers. RAG unit tests must use a deterministic
  local test embedding so `make test` stays offline; production indexing uses
  cached local `all-MiniLM-L6-v2`.
- GitHub writes are draft issue by default; a PR is draft-only and only from a
  pre-authored patch template. Never implement merge, infra mutation, or repo
  bypasses. Default to dry-run and test without network.
- Live GitHub access uses a fine-grained PAT scoped to the allowlisted repo:
  Metadata read, Issues read/write, Contents read/write, Pull requests
  read/write. Never require that token for tests.
- The LangGraph workflow is fixed: anomaly gate → correlate → hypothesize →
  remediate. Do not add supervisors or dynamic agent routing. The gate uses no
  LLM; graph state counts every LLM attempt and aborts at three calls. Use
  Pydantic structured outputs and keep correlation deterministic when possible.
- Keep the FastAPI surface small and typed. Persist incident runs in SQLite;
  never return secrets. Development may use the fake LLM, while non-development
  deployments require `X-API-KEY` when `API_KEY` is configured.
