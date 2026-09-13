from src.retrieval.keyword_search import keyword_search
from src.retrieval.vector_search import vector_search

RRF_K = 60

# Minimum best vector cosine-similarity score required to trust the results at
# all. Below this, we return nothing rather than let the agent answer from a
# weak match -- this is what lets it say "I don't have enough information"
# instead of confidently guessing. Chosen conservatively from observed scores
# on genuinely relevant questions (~0.6-0.7); tune against the eval set.
GROUNDEDNESS_THRESHOLD = 0.4


def hybrid_search(question: str, *, top_k: int = 5, company: str | None = None) -> list[dict]:
    """Combine Pinecone vector search and Snowflake keyword search results via
    reciprocal rank fusion, gated by a groundedness threshold on the vector
    scores.
    """
    candidate_pool = max(top_k * 4, 20)
    vector_results = vector_search(question, top_k=candidate_pool, company=company)
    if not vector_results or max(r["score"] for r in vector_results) < GROUNDEDNESS_THRESHOLD:
        return []

    keyword_results = keyword_search(question, top_k=candidate_pool, company=company)

    scores: dict[str, float] = {}
    chunks: dict[str, dict] = {}
    for rank, r in enumerate(vector_results):
        scores[r["chunk_id"]] = scores.get(r["chunk_id"], 0.0) + 1.0 / (RRF_K + rank + 1)
        chunks[r["chunk_id"]] = r
    for rank, r in enumerate(keyword_results):
        scores[r["chunk_id"]] = scores.get(r["chunk_id"], 0.0) + 1.0 / (RRF_K + rank + 1)
        chunks.setdefault(r["chunk_id"], r)

    ranked_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)[:top_k]
    return [{**chunks[cid], "rrf_score": scores[cid]} for cid in ranked_ids]
