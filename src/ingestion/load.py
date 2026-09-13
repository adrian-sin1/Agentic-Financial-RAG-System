from src.db.connection import get_snowflake_connection
from src.db.pinecone_client import get_pinecone_index

PINECONE_UPSERT_BATCH = 100


def load_document(*, document_id, company, year, document_type, source_filename):
    conn = get_snowflake_connection()
    cur = conn.cursor()
    cur.execute(
        """
        MERGE INTO documents t
        USING (SELECT %(document_id)s AS document_id) s
        ON t.document_id = s.document_id
        WHEN MATCHED THEN UPDATE SET
            company = %(company)s, year = %(year)s, document_type = %(document_type)s,
            source_filename = %(source_filename)s
        WHEN NOT MATCHED THEN INSERT (document_id, company, year, document_type, source_filename)
        VALUES (%(document_id)s, %(company)s, %(year)s, %(document_type)s, %(source_filename)s)
        """,
        {
            "document_id": document_id,
            "company": company,
            "year": year,
            "document_type": document_type,
            "source_filename": source_filename,
        },
    )
    conn.commit()
    conn.close()


def replace_document_chunks(document_id: str, new_chunk_ids: list[str]):
    """Delete any existing chunks for this document whose chunk_id isn't in the
    new set being loaded. Needed whenever re-ingestion produces a different set
    of chunk_ids than before (e.g. a chunking-strategy change) -- MERGE/upsert
    alone only adds or updates, it never removes chunks that no longer exist
    under the new scheme, which would otherwise leave stale, duplicate content
    silently polluting search results forever.
    """
    conn = get_snowflake_connection()
    cur = conn.cursor()
    cur.execute("SELECT chunk_id FROM document_chunks WHERE document_id = %s", (document_id,))
    existing_ids = {row[0] for row in cur.fetchall()}
    stale_ids = existing_ids - set(new_chunk_ids)

    if stale_ids:
        cur.executemany("DELETE FROM document_chunks WHERE chunk_id = %s", [(cid,) for cid in stale_ids])
        conn.commit()
    conn.close()

    if stale_ids:
        get_pinecone_index().delete(ids=list(stale_ids))


def load_chunks(chunks: list[dict]):
    """MERGE chunk text/metadata into Snowflake and upsert embeddings into Pinecone.
    Both are keyed by chunk_id, so re-running ingestion overwrites instead of
    duplicating rows/vectors. Call replace_document_chunks() first if the set of
    chunk_ids for this document may have changed since the last run.
    """
    conn = get_snowflake_connection()
    cur = conn.cursor()
    cur.executemany(
        """
        MERGE INTO document_chunks t
        USING (SELECT %(chunk_id)s AS chunk_id) s
        ON t.chunk_id = s.chunk_id
        WHEN MATCHED THEN UPDATE SET
            document_id = %(document_id)s, company = %(company)s, year = %(year)s,
            document_type = %(document_type)s, section = %(section)s, page = %(page)s,
            chunk_text = %(chunk_text)s
        WHEN NOT MATCHED THEN INSERT
            (chunk_id, document_id, company, year, document_type, section, page, chunk_text)
        VALUES
            (%(chunk_id)s, %(document_id)s, %(company)s, %(year)s, %(document_type)s,
             %(section)s, %(page)s, %(chunk_text)s)
        """,
        chunks,
    )
    conn.commit()
    conn.close()

    index = get_pinecone_index()
    vectors = [
        {
            "id": c["chunk_id"],
            "values": c["embedding"],
            "metadata": {"company": c["company"], "year": c["year"], "section": c["section"]},
        }
        for c in chunks
    ]
    for i in range(0, len(vectors), PINECONE_UPSERT_BATCH):
        index.upsert(vectors=vectors[i : i + PINECONE_UPSERT_BATCH])
