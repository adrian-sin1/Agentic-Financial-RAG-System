from src.retrieval.companies import normalize_company_name
from src.retrieval.keyword_search import keyword_search
from src.retrieval.neighbors import fetch_chunks, neighbor_chunk_ids
from src.retrieval.rerank import rerank_chunks
from src.retrieval.vector_search import vector_search

RRF_K = 60

# Minimum best vector cosine-similarity score required to trust the results at
# all. Below this, we return nothing rather than let the agent answer from a
# weak match -- this is what lets it say "I don't have enough information"
# instead of confidently guessing. Chosen conservatively from observed scores
# on genuinely relevant questions (~0.6-0.7); tune against the eval set.
GROUNDEDNESS_THRESHOLD = 0.4


def hybrid_search(
    question: str,
    *,
    top_k: int = 5,
    company: str | None = None,
    expand_neighbors: bool = True,
    rerank: bool = False,
) -> list[dict]:
    """Combine Pinecone vector search and Snowflake keyword search results via
    reciprocal rank fusion, gated by a groundedness threshold on the vector
    scores.

    If rerank is set, the RRF-ranked candidate pool (not just the final top_k)
    is re-scored by a Hugging Face-hosted cross-encoder before being cut down
    to top_k -- RRF only combines two independently-computed rankings, so a
    chunk that's genuinely relevant but landed just outside the cutoff on both
    signals can, in principle, be recovered here, since the reranker reads the
    question and each chunk's text together. Defaults to False: live-tested
    against this eval set, the reranker actually hurt retrieval accuracy
    (81% vs. 88%) by over-concentrating on one section instead of surfacing
    a shorter-but-correct one (see ROADMAP.md). Kept available, off by
    default, rather than deleted.

    If expand_neighbors is set, each retrieved chunk's immediate neighbors
    (same section, adjacent index) are pulled in too -- if paragraph B
    references paragraph A and they landed in different chunks, retrieving B
    brings A along even though A didn't independently rank in the top_k.
    Neighbors are marked is_neighbor=True and carry no rrf_score/rerank_score,
    since they weren't independently judged relevant, just adjacent to
    something that was.
    """
    company = normalize_company_name(company)
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

    pool_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)[:candidate_pool]

    if rerank:
        reranked = rerank_chunks(question, [chunks[cid] for cid in pool_ids], top_n=top_k)
        ranked_ids = [c["chunk_id"] for c in reranked]
        results = [{**c, "rrf_score": scores[c["chunk_id"]], "is_neighbor": False} for c in reranked]
    else:
        ranked_ids = pool_ids[:top_k]
        results = [
            {**chunks[cid], "rrf_score": scores[cid], "rerank_score": None, "is_neighbor": False}
            for cid in ranked_ids
        ]

    if expand_neighbors:
        wanted_ids = set()
        for cid in ranked_ids:
            wanted_ids.update(neighbor_chunk_ids(cid))
        wanted_ids -= set(ranked_ids)

        neighbor_chunks = fetch_chunks(list(wanted_ids))
        for chunk in neighbor_chunks.values():
            results.append({**chunk, "rrf_score": None, "rerank_score": None, "is_neighbor": True})

    return results
