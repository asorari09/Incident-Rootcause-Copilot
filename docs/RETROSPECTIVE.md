# Build retrospective

## What worked

- Phased checkpoints prevented UI work from getting ahead of the detector, RAG, GitHub guardrails, or graph budget tests.
- The deterministic scenarios made it possible to test a real end-to-end shape without a Prometheus cluster or production secrets.
- Dry-run GitHub artifacts made the demo visible without needing a real token or allowing a mutation in tests.

## Real friction and responses

### Offline model and integration tests

Chroma and MiniLM are useful for the real retrieval path, but downloading a model during unit tests would violate the offline test requirement. The RAG tests use a deterministic local hash embedding, while production indexing uses local MiniLM. `FakeLLM` similarly lets graph, API, and eval tests exercise structured outputs without an OpenAI key or spend.

### Chroma embedding-function compatibility

The installed Chroma version expected document/query embedding methods and embedding-function configuration hooks. The custom local test embedding was adjusted to support those methods, and the retrieval tests now run cleanly offline.

### Cost budget semantics

The normal graph path intentionally has two LLM nodes. The third allowed call is not an extra agent: it is reserve for a single Pydantic structured-output retry. A graph test injects invalid fake output and verifies it returns `budget_exceeded` rather than looping.

### Local web/API integration

The frontend initially had no backend boundary. Vite proxy rules now route the small API surface to port 8000, so local development does not need browser CORS configuration. The dashboard deliberately says “Offline fake LLM · dry-run GitHub” rather than implying a live production integration.

### Docker / Render hosting

Local `docker build` was blocked once by a missing Docker daemon, but the same Dockerfile now runs on Render Free as a single service: https://ir-copilot.onrender.com. Free-tier constraints forced two deliberate choices: skip MiniLM boot indexing (`ENABLE_RUNBOOK_INDEX=false`) and keep `ALLOW_FAKE_LLM=true` so the public demo needs no paid keys and stays within ~512 MB RAM. Cold starts after idle spin-down take about a minute.

### Observability boundary

Langfuse is implemented as an optional callback. Without configured keys it is a no-op, which preserves offline tests. A stronger portfolio claim still needs actual Langfuse credentials and a visible trace before saying “cloud observability evidence.”

## What I would improve next

Add customer-specific metric adapters (e.g. Prometheus) and more eval cases before expanding autonomy. Optionally configure a scoped GitHub App / live draft issues and a real Langfuse project for screenshots — without changing the draft-only guardrails.
