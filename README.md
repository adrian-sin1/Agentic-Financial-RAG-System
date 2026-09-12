# Agentic Financial RAG LLM

An agentic RAG platform for answering questions over company financial filings (10-Ks),
combining unstructured document retrieval with structured financial data lookups.

## Stack

- **LLM/embeddings:** OpenAI (`text-embedding-3-small` + GPT) end-to-end
- **Vector store:** Pinecone (embeddings only, keyed by `chunk_id`)
- **System of record:** Snowflake (`documents`, `document_chunks`, `financial_metrics`, `query_log`)
- **Structured financials:** SEC EDGAR XBRL companyfacts API
- **Agent orchestration:** LangGraph
- **API:** FastAPI

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env  # fill in Snowflake / Pinecone / OpenAI credentials
```

Run the DDL in [src/db/schema.sql](src/db/schema.sql) against your Snowflake database/schema,
then create a Pinecone index (dimension 1536, cosine metric) for `text-embedding-3-small`.

Verify connectivity:

```bash
python -m src.db.verify_setup
```

## Project layout

```
src/
├── ingestion/   # extract, clean, chunk, embed, load
├── retrieval/   # hybrid_search(), query_financials()
├── agent/       # LangGraph graph definition
├── api/         # FastAPI app
└── db/          # Snowflake connection + schema DDL
tests/
eval/
  └── golden_questions.jsonl
data/raw/        # local scratch, gitignored
```
