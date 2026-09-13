from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.agent.graph import answer_question
from src.api.auth import verify_api_key
from src.api.schemas import (
    ChatRequest,
    ChatResponse,
    DocumentIngestRequest,
    DocumentIngestResponse,
    DocumentInfo,
    HealthResponse,
    SourceInfo,
)
from src.db.connection import get_snowflake_connection
from src.ingestion.run import ingest

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Agentic Financial RAG API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
def chat(request: Request, body: ChatRequest):
    result = answer_question(body.question)

    seen = set()
    sources = []
    for r in result["hybrid_results"]:
        key = ("filing", r["company"], r["year"], r["section"])
        if key not in seen:
            seen.add(key)
            sources.append(SourceInfo(type="filing", company=r["company"], year=r["year"], detail=r["section"]))
    for r in result["sql_results"]:
        if not r:
            continue
        key = ("financial_metric", r["company"], r["year"], r["metric_name"])
        if key not in seen:
            seen.add(key)
            sources.append(
                SourceInfo(type="financial_metric", company=r["company"], year=r["year"], detail=r["metric_name"])
            )

    return ChatResponse(answer=result["answer"], tool_calls=result["tool_calls"], sources=sources)


@app.get("/documents", response_model=list[DocumentInfo], dependencies=[Depends(verify_api_key)])
def list_documents():
    conn = get_snowflake_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT document_id, company, year, document_type, source_filename "
        "FROM documents ORDER BY ingested_at DESC"
    )
    rows = cur.fetchall()
    conn.close()
    return [
        DocumentInfo(document_id=r[0], company=r[1], year=r[2], document_type=r[3], source_filename=r[4])
        for r in rows
    ]


@app.post("/documents", response_model=DocumentIngestResponse, dependencies=[Depends(verify_api_key)])
def add_document(body: DocumentIngestRequest):
    result = ingest(
        company=body.company,
        year=body.year,
        document_type=body.document_type,
        stage_path=body.stage_path,
        source_filename=body.source_filename,
    )
    return DocumentIngestResponse(**result)


app.mount("/ui", StaticFiles(directory="frontend/dist", html=True), name="ui")
