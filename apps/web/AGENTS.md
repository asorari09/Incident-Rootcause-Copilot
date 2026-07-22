# Web guidance

Read the root `AGENTS.md` and `END_TO_END_PLAN.md` first. Use React, Vite, and
TypeScript for a small operator dashboard, not a design exercise.

- Preserve the human-in-the-loop message: GitHub artifacts are drafts requiring
  review; never present automated remediation as an action.
- Show deterministic detection, compact evidence, trace steps, GitHub draft
  status, and cost only when their backend phases exist.
- Do not add LLM calls, API secrets, or direct GitHub/infra mutation from the
  browser. Keep dependencies and UI complexity minimal.
