import re

import tiktoken

CHUNK_TOKENS = 500
OVERLAP_TOKENS = 50

_encoding = tiktoken.get_encoding("cl100k_base")


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:60]


def _split_oversized_paragraph(paragraph: str) -> list[str]:
    """Fall back to raw token-slicing for a single paragraph too big to fit in
    one chunk on its own (e.g. a large table)."""
    tokens = _encoding.encode(paragraph)
    pieces = []
    start = 0
    while start < len(tokens):
        end = min(start + CHUNK_TOKENS, len(tokens))
        pieces.append(_encoding.decode(tokens[start:end]))
        start = end
    return pieces


def chunk_sections(
    sections: list[dict], *, company: str, year: int, document_type: str, document_id: str
) -> list[dict]:
    """Pack whole paragraphs into ~CHUNK_TOKENS-token chunks, never splitting a
    paragraph across two chunks unless it alone exceeds the limit -- this keeps
    a complete thought inside one chunk instead of cutting mid-sentence at a
    fixed token count. The last paragraph of each chunk is carried over as the
    start of the next one, so context isn't lost right at the boundary.

    chunk_id is deterministic (document_id + section + index) so re-running
    ingestion after a bug fix upserts the same rows/vectors instead of
    duplicating them.
    """
    chunks = []
    for section in sections:
        section_slug = _slugify(section["section"])
        idx = 0
        current: list[str] = []
        current_tokens = 0

        def emit(paragraphs: list[str]) -> None:
            nonlocal idx
            chunks.append(
                {
                    "chunk_id": f"{document_id}::{section_slug}::{idx}",
                    "document_id": document_id,
                    "company": company,
                    "year": year,
                    "document_type": document_type,
                    "section": section["section"],
                    "page": None,
                    "chunk_text": "\n\n".join(paragraphs),
                }
            )
            idx += 1

        for paragraph in section["paragraphs"]:
            para_tokens = len(_encoding.encode(paragraph))

            if para_tokens > CHUNK_TOKENS:
                if current:
                    emit(current)
                    current, current_tokens = [], 0
                for piece in _split_oversized_paragraph(paragraph):
                    emit([piece])
                continue

            if current and current_tokens + para_tokens > CHUNK_TOKENS:
                emit(current)
                overlap = current[-1]
                current = [overlap]
                current_tokens = len(_encoding.encode(overlap))

            current.append(paragraph)
            current_tokens += para_tokens

        if current:
            emit(current)

    return chunks
