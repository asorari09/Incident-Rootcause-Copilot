# IR-Copilot demo script

## Before the demo

**Hosted (recommended for interviews):** open
[https://ir-copilot.onrender.com](https://ir-copilot.onrender.com).
If the free instance was idle, wait ~1 minute for cold start, then proceed.

**Local alternative:** from the repository root, use two terminals:

```sh
make run-api
make run-web
```

Open `http://127.0.0.1:5173`. Local development uses the Vite proxy and the dashboard sends `use_fake_llm=true`, so no OpenAI key or spend is required. GitHub remains dry-run unless the environment is intentionally changed.

## 3-minute version

1. **Set the context (20s).** “This is a human-in-the-loop incident copilot. Statistics decide whether an anomaly is real; the agent only interprets bounded evidence and drafts a human-reviewable artifact.”
2. **Inject (20s).** Select `sc_db_pool` and click **Inject**. Point to error rate, latency, and DB pool charts.
3. **Run (35s).** Click **Run incident**. Show the completed status, high severity, `db_connection_pool_exhaustion`, evidence, and `2 / 3` LLM calls.
4. **Trace (25s).** Read the trace: gate passed, correlation retrieved context, structured hypothesis, draft remediation.
5. **Guardrail (25s).** Show the dry-run outbox path and say no PR merge, deploy, or infrastructure action exists.
6. **False alarm (35s).** Choose `sc_noise_false_alarm`, run it, and show `skipped` and `0 / 3` calls.
7. **Proof (20s).** Run `make eval`: the current fake result is `5/5 exact`, `noise_skip=True`, `mean_cost=$0.0000`.

## 8-minute version

Use the 3-minute script, then add:

1. **API inspection (60s).** Open `http://127.0.0.1:8000/docs`. Use `GET /scenarios`, `POST /scenarios/{id}/inject`, `POST /incidents/run`, and `GET /incidents/{id}` to show the narrow OpenAPI surface.
2. **Curl fallback (60s).** Demonstrate without the UI:

   ```sh
   curl -X POST http://127.0.0.1:8000/scenarios/sc_db_pool/inject
   curl -X POST http://127.0.0.1:8000/incidents/run \
     -H 'Content-Type: application/json' \
     -d '{"scenario_id":"sc_db_pool","use_fake_llm":true}'
   ```

3. **Detector details (60s).** Explain the 30-point rolling baseline and the DB composite rule in `detection/detector.py`. Emphasize that the model never looks at the raw chart to decide an alert.
4. **RAG and evidence (60s).** Explain `data/runbooks`, `rag/indexer.py`, Chroma, local MiniLM, top-k=3, and the compact EvidencePack.
5. **Cost and evals (60s).** Show `make eval`; explain fake cost is exactly zero for offline CI, while live configuration is restricted to mini and the golden live budget is $0.03/run.
6. **Integration boundary (60s).** Open an outbox Markdown artifact. It contains incident ID, labels, proposed content, and a reasoning trace. Explain that a real PAT is optional and scoped to one repo.
7. **Deployment (40s).** Show `Dockerfile`, `render.yaml`, and the live Render Free URL. Mention scale-to-sleep after idle and the ~1 minute cold start — a deliberate free-tier tradeoff.
