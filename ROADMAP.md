# Roadmap

Status of each build phase for the Agentic Financial RAG Platform.

## Done

- [x] **Phase 0 — Repo & environment setup**
  Snowflake (database, schema, service user with key-pair auth), Pinecone index (1536-dim, cosine), OpenAI connectivity, `.env`/`.gitignore`, verified end to end with `verify_setup.py`.

- [x] **Phase 1 — MVP ingestion + vector-only retrieval**
  Apple FY2025 10-K ingested: extract (SEC inline-XBRL HTML → text) → clean → chunk → embed → idempotent load into Snowflake + Pinecone. `scripts/ask.py` answers questions with cited sources.

- [x] **Phase 2 — Structured data + hybrid search**
  `financials.py` pulls exact figures from SEC EDGAR's XBRL API into `financial_metrics`. Keyword search (ILIKE + phrase-weighted bigrams) fused with vector search via reciprocal rank fusion, gated by a groundedness threshold. 16-question eval set + `run_eval.py`.

- [x] **Phase 3 — LangGraph agent**
  Router node (LLM-driven) decides `hybrid_search` / `sql_tool` / both / neither. Synthesis frames filing excerpts as untrusted reference material and skips the LLM call entirely when nothing is grounded. Every query logged to `query_log`.

- [x] **Phase 4 — FastAPI + logging + minimal UI**
  `POST /chat`, `GET`/`POST /documents`, `GET /health`. API key auth + per-IP rate limiting on `/chat`. A small React (Vite) chat UI served through FastAPI's static files.

- [x] **Phase 5 — Testing**
  62 pytest tests across ingestion, retrieval, agent routing (LLM mocked), and the API (auth, rate limiting, error handling) — all mocked at the external boundary, no live network/DB calls, ~3s to run.

- [x] **Phase 6 — Docker + CI/CD**
  Multi-stage Dockerfile (Node build → Python deps → slim runtime, 472MB). GitHub Actions: pytest → eval-score gate → Docker build validation → (on push to `main`) build + push to GHCR → trigger a Render deploy hook. Live and verified: `/health`, `/chat`, and `/ui` all confirmed working on the deployed service.

- [x] **Phase 7 — Scale up**
  Added Microsoft, Alphabet, Amazon, and Meta (FY2025 + FY2024 each), plus Apple's FY2024 — 10 documents, 2,160 chunks, 40 financial metrics total. Caught and fixed a real extraction bug along the way (section-header detection only worked on Apple's exact HTML formatting; see the `extract.py` fix). Eval score held at 14/16 (88%) after scaling the corpus 10x — same one known near-miss as before, no new failures from cross-company interference. Spot-checked structured + text retrieval for all 4 new companies individually.

## Known limitations (tracked, not blocking)

- One eval question (Legal Proceedings) narrowly misses hybrid search's top-5 cutoff — the content is retrievable (confirmed present ~rank 10-18) but doesn't rank high enough for this specific phrasing. Eval score: 14/16 (88%), above the 80% pass threshold.
- The LLM router is not perfectly deterministic — the same question can occasionally select a different subset of tools across runs. Phase 5's agent tests mock the routing decision specifically to sidestep this in CI.
