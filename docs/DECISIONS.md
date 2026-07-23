# Architecture decisions

This is the implemented ADR-style version of Decision Log D1–D20.

| ID | Decision | Implemented choice | Evidence |
|---|---|---|---|
| D1 | Product | IR-Copilot | Root README and package names |
| D2 | Orchestration | Fixed LangGraph state machine | `graph/build.py` |
| D3 | Supervisor | None | Deterministic graph edges only |
| D4 | Detection | Rolling z-score, percent change, composite rules | `detection/detector.py` |
| D5 | Metrics MVP | Synthetic `ScenarioEngine` | `scenarios/engine.py` and five JSON files |
| D6 | LLM | `gpt-4o-mini`, temperature 0 | `config.py`, `graph/llm.py` |
| D7 | Embeddings | Local `all-MiniLM-L6-v2` | `rag/embeddings.py` |
| D8 | Vector store | Persistent Chroma | `rag/indexer.py` |
| D9 | GitHub auth MVP | Fine-grained PAT, one allowlisted repo | `github/config.py` |
| D10 | Default remediation | Draft issue; template-only draft PR helper | `github/client.py` |
| D11 | Auto-merge / execution | Never | No merge or infrastructure-mutation tool exists; source tests enforce this |
| D12 | Observability | Optional Langfuse callback | `graph/observability.py` |
| D13 | API | FastAPI | `main.py`, `api/routes.py` |
| D14 | Web | React + Vite + TypeScript | `apps/web` |
| D15 | Run persistence | SQLite | `api/store.py` |
| D16 | Deploy | Single Docker service, Railway-ready | `Dockerfile`, `railway.toml` |
| D17 | Packages | uv for Python, npm for web | `pyproject.toml`, `apps/web/package.json` |
| D18 | Cost cap | Max 3 LLM attempts/run | `AppSettings` and graph tests |
| D19 | CI network | Offline tests with fake/dry-run paths | `make test`, `FakeLLM` |
| D20 | License | MIT | `LICENSE` |

The decisions intentionally favor auditability, reproducibility, and a small operational surface over a more autonomous-looking demo.
