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
  Added Microsoft, Alphabet, Amazon, and Meta (FY2025 + FY2024 each), plus Apple's FY2024 — 10 documents, 2,160 chunks, 40 financial metrics total. Caught and fixed three real bugs that only surfaced once more than one company shared the same index: (1) section-header detection only worked on Apple's exact HTML formatting (`extract.py`), (2) the agent never filtered `hybrid_search` by company, so an Apple question could return Meta/Alphabet sources (`router.py`/`graph.py`), (3) colloquial company names ("Google", "Facebook") don't match the stored legal entity names ("Alphabet", "Meta"), silently returning nothing (`companies.py`). Eval score held at 14/16 (88%) after scaling the corpus 10x.

- [x] **Post-launch hardening — eval router coverage, least privilege, observability**
  (1) `eval/run_eval.py` now calls `route()` directly for each golden question and checks whether the router picked the correct tool(s) (`use_hybrid_search`/`use_sql_tool`) against expectations derived from the question's `type` field, reported as a separate score from retrieval accuracy (100% router accuracy, 88% retrieval accuracy as of last run). (2) `financial_rag_svc` no longer runs under a blanket `SYSADMIN` role — `FINANCIAL_RAG_APP_ROLE` (`src/db/least_privilege_role.sql`) grants only `SELECT`/`INSERT`/`UPDATE`/`DELETE` on the 4 app tables, read-only stage access, and warehouse/database/schema usage; no `CREATE`/`ALTER`/`DROP`/`OWNERSHIP`. (3) `query_log` now records which chunks actually grounded each answer (`documents_retrieved`: chunk_id/company/year/section/is_neighbor, no chunk text) and which exact `(company, year, metric)` params `sql_tool` was called with (`sql_queries_used`), not just that the tools ran.

## Known limitations (tracked, not blocking)

- One eval question (Legal Proceedings) narrowly misses hybrid search's top-5 cutoff — the content is retrievable (confirmed present ~rank 10-18) but doesn't rank high enough for this specific phrasing. Eval score: 14/16 (88%), above the 80% pass threshold.
- The LLM router is not perfectly deterministic — the same question can occasionally select a different subset of tools across runs. Phase 5's agent tests mock the routing decision specifically to sidestep this in CI.
- Multi-company **text/qualitative** comparisons (e.g. "compare Apple and Microsoft's risk factors") don't work well — `hybrid_search_company` only holds one company, so a genuinely comparative question falls back to an unfiltered search and can pull sources from companies not even asked about. It fails safely (the model admits it lacks the other company's data rather than guessing), but doesn't fully answer the question. Multi-company **structured** comparisons ("compare Apple and Microsoft's revenue") already work correctly, since `sql_queries` was list-based from the start.
