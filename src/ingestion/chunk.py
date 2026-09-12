import re

import tiktoken

CHUNK_TOKENS = 500
OVERLAP_TOKENS = 50

_encoding = tiktoken.get_encoding("cl100k_base")


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:60]


def chunk_sections(
    sections: list[dict], *, company: str, year: int, document_type: str, document_id: str
) -> list[dict]:
    """Split cleaned sections into ~CHUNK_TOKENS-token chunks with OVERLAP_TOKENS
    overlap, attaching the metadata needed to store each chunk in Snowflake/Pinecone.

    chunk_id is deterministic (document_id + section + index) so re-running ingestion
    after a bug fix upserts the same rows/vectors instead of duplicating them.
    """
    chunks = []
    for section in sections:
        tokens = _encoding.encode(section["text"])
        section_slug = _slugify(section["section"])
        idx = 0
        start = 0
        while start < len(tokens):
            end = min(start + CHUNK_TOKENS, len(tokens))
            chunk_text = _encoding.decode(tokens[start:end])
            chunks.append(
                {
                    "chunk_id": f"{document_id}::{section_slug}::{idx}",
                    "document_id": document_id,
                    "company": company,
                    "year": year,
                    "document_type": document_type,
                    "section": section["section"],
                    "page": None,
                    "chunk_text": chunk_text,
                }
            )
            idx += 1
            if end == len(tokens):
                break
            start = end - OVERLAP_TOKENS
    return chunks
