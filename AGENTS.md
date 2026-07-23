# IR-Copilot repository guidance

Read `END_TO_END_PLAN.md` before any architectural change. It is authoritative;
Decision Log D1–D20 is binding. Work one §14 phase at a time and verify its
checkpoint before proceeding.

## Commands

- `make install` installs Python with uv and the web dependencies.
- `make test` must pass offline.
- `make run-api`, `make run-web`, `make eval`, and `make index-runbooks` are the
  standard entry points as their phases are implemented.
- Hosted demos use Render Free (`render.yaml`, `docs/DEPLOY.md`) with
  `ALLOW_FAKE_LLM=true` and `ENABLE_RUNBOOK_INDEX=false`.

## Git / phase discipline (mandatory)

- After each phase checkpoint passes (`make test` green + phase verification),
  create **one git commit** for that phase before starting the next phase.
- Working tree must be clean (aside from ignored runtime artifacts) when a phase
  is marked complete.
- Commit message style: `Phase N: <short why/what>` (e.g. `Phase 6: add operator dashboard for incident demos`).
- Never commit secrets (`.env`), `data/chroma/*` contents, `data/outbox/*`
  artifacts, `*.sqlite3`, `node_modules/`, or `.venv/`.
- Do not use `--no-verify`, force push, or amend unless the human explicitly asks.

## Invariants

- Only `gpt-4o-mini` is permitted for MVP, at temperature 0, with at most three
  LLM calls per incident. Prefer the deterministic anomaly gate and local
  MiniLM embeddings; never add a supervisor agent or unbounded loops.
- GitHub remediation is draft-only. Never add auto-merge, deploy, delete,
  kubectl, cloud mutation, or other infrastructure mutation tools.
- Keep `GITHUB_DRY_RUN=true` as the default. Only the configured allowlisted
  repository may be used when live GitHub support is implemented.
- Keep tests network-free: mock integrations and use dry-run paths. Detector
  code must not import LLM clients.
- Never commit secrets. Do not create `CLAUDE.md` or `.claude/` files.

Keep code simple and shallow. Put deep design in `END_TO_END_PLAN.md`, not here.
If the same mistake recurs twice, add a concise rule to the nearest `AGENTS.md`.

The public implementation narrative lives in `docs/` after Phase 9. Keep those
files grounded in actual commands and measured results; do not claim configured
live integrations or deployments that have not been verified.
