from src.db.connection import get_snowflake_connection


def fetch_chunks(chunk_ids: list[str]) -> dict[str, dict]:
    """Fetch chunk text/metadata for a list of chunk_ids from Snowflake, keyed
    by chunk_id. Missing ids (e.g. a neighbor that doesn't exist because it's
    past the start/end of the section) are simply absent from the result.
    """
    if not chunk_ids:
        return {}
    conn = get_snowflake_connection()
    cur = conn.cursor()
    placeholders = ", ".join(["%s"] * len(chunk_ids))
    cur.execute(
        f"SELECT chunk_id, company, year, document_type, section, page, chunk_text "
        f"FROM document_chunks WHERE chunk_id IN ({placeholders})",
        chunk_ids,
    )
    rows = cur.fetchall()
    conn.close()
    return {
        r[0]: {
            "chunk_id": r[0],
            "company": r[1],
            "year": r[2],
            "document_type": r[3],
            "section": r[4],
            "page": r[5],
            "chunk_text": r[6],
        }
        for r in rows
    }


def neighbor_chunk_ids(chunk_id: str) -> list[str]:
    """Given a chunk_id like "apple_2025_10-k::item-1a-risk-factors::7", return
    the chunk_ids immediately before and after it in the same section (chunk.py
    encodes ordering as document_id::section_slug::index). If paragraph B
    references paragraph A and they landed in adjacent chunks, retrieving B
    pulls A along too, regardless of exactly where the chunk boundary fell.
    """
    document_id, section_slug, idx_str = chunk_id.rsplit("::", 2)
    idx = int(idx_str)
    ids = [f"{document_id}::{section_slug}::{idx + 1}"]
    if idx > 0:
        ids.append(f"{document_id}::{section_slug}::{idx - 1}")
    return ids
