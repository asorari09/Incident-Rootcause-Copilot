# IR-Copilot

Detect with stats. Diagnose with agents. Remediate with humans.

IR-Copilot is a human-in-the-loop incident assistant. It uses deterministic
anomaly detection before a fixed, cost-bounded agent pipeline grounds a
diagnosis in runbooks and GitHub context. Remediation is always draft-only.

## Status

Phase 5 API checkpoint. Follow the authoritative
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
