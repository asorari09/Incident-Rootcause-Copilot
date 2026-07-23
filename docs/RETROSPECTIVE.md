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

### Docker verification gap

The Dockerfile, compose configuration, static SPA serving test, Python tests, and web build all passed. `docker build -t ir-copilot .` could not run here because Docker was installed but the daemon socket was unavailable. This is recorded rather than presented as a successful image build. The next verification step is to start Docker Desktop, build the image, run it with `.env`, and hit `/health` and `/`.

### Observability boundary

Langfuse is implemented as an optional callback. Without configured keys it is a no-op, which preserves offline tests. A production demo still needs actual Langfuse credentials and a visible trace before claiming cloud observability evidence.

## What I would improve next

Add customer-specific metric adapters and eval cases before expanding autonomy. Then verify the container on a running Docker daemon, configure an intentionally scoped GitHub App, and collect a real Langfuse trace with a non-secret demo project.
