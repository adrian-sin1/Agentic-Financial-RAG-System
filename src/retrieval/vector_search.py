import os

from dotenv import load_dotenv
from openai import OpenAI

from src.db.pinecone_client import get_pinecone_index
from src.retrieval.neighbors import fetch_chunks

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
    if not matches:
        return []

    chunks_by_id = fetch_chunks([m["id"] for m in matches])

    results_out = []
    for match in matches:
        chunk = chunks_by_id.get(match["id"])
        if chunk is None:
            continue
        results_out.append({**chunk, "score": match["score"]})
    return results_out
