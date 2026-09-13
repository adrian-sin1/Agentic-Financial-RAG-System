import re

from src.db.connection import get_snowflake_connection

STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "for", "to", "and", "or", "is", "are",
    "what", "did", "does", "how", "with", "that", "this", "it", "its", "was",
    "were", "has", "have", "had", "by", "from", "as", "at", "be", "which",
}


def _keywords(question: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z0-9]+", question.lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 2]


def _phrases(question: str) -> list[str]:
    """Consecutive-keyword bigrams (e.g. "legal proceedings"). Weighted higher
    than individual keywords in keyword_search, since a chunk matching the
    exact phrase from the question is a much stronger signal than matching
    each word separately/scattered.
    """
    keywords = _keywords(question)
    return [f"{a} {b}" for a, b in zip(keywords, keywords[1:])]


def keyword_search(question: str, *, top_k: int = 5, company: str | None = None) -> list[dict]:
    """Plain ILIKE keyword search over chunk_text, ranked by how many distinct
    keywords/phrases from the question each chunk matches (phrase matches
    count for more than single-word matches).
    """
    keywords = _keywords(question)
    if not keywords:
        return []
    phrases = _phrases(question)

    PHRASE_WEIGHT = 3
    match_terms = ["IFF(chunk_text ILIKE %s, 1, 0)" for _ in keywords] + [
        f"IFF(chunk_text ILIKE %s, {PHRASE_WEIGHT}, 0)" for _ in phrases
    ]
    match_expr = " + ".join(match_terms)
    or_clause = " OR ".join(["chunk_text ILIKE %s"] * (len(keywords) + len(phrases)))
    score_params = [f"%{kw}%" for kw in keywords] + [f"%{p}%" for p in phrases]
    where_params = [f"%{kw}%" for kw in keywords] + [f"%{p}%" for p in phrases]

    where_sql = f"({or_clause})"
    params = score_params + where_params
    if company:
        where_sql += " AND company = %s"
        params.append(company)
    params.append(top_k)

    query = f"""
        SELECT chunk_id, company, year, document_type, section, page, chunk_text,
               ({match_expr}) AS match_count
        FROM document_chunks
        WHERE {where_sql}
        ORDER BY match_count DESC
        LIMIT %s
    """

    conn = get_snowflake_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "chunk_id": r[0],
            "company": r[1],
            "year": r[2],
            "document_type": r[3],
            "section": r[4],
            "page": r[5],
            "chunk_text": r[6],
            "match_count": r[7],
        }
        for r in rows
    ]
