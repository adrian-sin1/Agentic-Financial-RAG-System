import os

from dotenv import load_dotenv
from openai import OpenAI

from src.db.connection import get_snowflake_connection
from src.db.pinecone_client import get_pinecone_index

load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-small"


def vector_search(question: str, *, top_k: int = 5, company: str | None = None) -> list[dict]:
    """Embed the question, query Pinecone for the top-k nearest chunk vectors
    (optionally filtered by company), then fetch the matching chunk text/metadata
    from Snowflake by chunk_id.
    """
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    embedding = client.embeddings.create(model=EMBEDDING_MODEL, input=question).data[0].embedding

    index = get_pinecone_index()
    query_filter = {"company": company} if company else None
    results = index.query(vector=embedding, top_k=top_k, filter=query_filter, include_metadata=True)

    matches = results.get("matches", [])
    chunk_ids = [m["id"] for m in matches]
    if not chunk_ids:
        return []

    conn = get_snowflake_connection()
    cur = conn.cursor()
    placeholders = ", ".join(["%s"] * len(chunk_ids))
    cur.execute(
        f"SELECT chunk_id, company, year, document_type, section, page, chunk_text "
        f"FROM document_chunks WHERE chunk_id IN ({placeholders})",
        chunk_ids,
    )
    rows_by_id = {row[0]: row for row in cur.fetchall()}
    conn.close()

    results_out = []
    for match in matches:
        row = rows_by_id.get(match["id"])
        if row is None:
            continue
        results_out.append(
            {
                "chunk_id": row[0],
                "company": row[1],
                "year": row[2],
                "document_type": row[3],
                "section": row[4],
                "page": row[5],
                "chunk_text": row[6],
                "score": match["score"],
            }
        )
    return results_out
