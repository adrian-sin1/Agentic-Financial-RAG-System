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

## Not started

- [ ] **Phase 7 — Scale up**
  Add the remaining 4 companies × 2 years once Phases 1–6 are solid end to end; re-run the eval set to confirm quality holds at scale.

## Known limitations (tracked, not blocking)

- Two eval questions (Legal Proceedings, Business-section combined query) narrowly miss hybrid search's top-5 cutoff — the content is retrievable (confirmed present ~rank 10-18) but doesn't rank high enough for these specific phrasings. Eval score: 13/16 (81%), above the 80% pass threshold.
- The LLM router is not perfectly deterministic — the same question can occasionally select a different subset of tools across runs. Phase 5's agent tests mock the routing decision specifically to sidestep this in CI.
