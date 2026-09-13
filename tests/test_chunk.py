from src.ingestion.chunk import CHUNK_TOKENS, _encoding, _slugify, chunk_sections

COMMON_KWARGS = dict(company="Apple", year=2025, document_type="10-K", document_id="apple_2025_10-k")


def _words(n_tokens: int) -> str:
    """A paragraph that encodes to roughly n_tokens tokens."""
    text = " ".join(["word"] * n_tokens)
    # tiktoken may merge/split differently than 1 token/word; trim/pad to exact count
    tokens = _encoding.encode(text)
    if len(tokens) > n_tokens:
        tokens = tokens[:n_tokens]
    return _encoding.decode(tokens)


def test_slugify_produces_url_safe_lowercase_id():
    assert _slugify("Item 1A. Risk Factors") == "item-1a-risk-factors"
    assert _slugify("Item 9C. Disclosure Regarding Foreign Jurisdictions!") == (
        "item-9c-disclosure-regarding-foreign-jurisdictions"
    )


def test_small_section_fits_in_one_chunk():
    sections = [{"section": "Item 2. Properties", "paragraphs": [_words(50), _words(50)]}]
    chunks = chunk_sections(sections, **COMMON_KWARGS)
    assert len(chunks) == 1
    assert chunks[0]["chunk_id"] == "apple_2025_10-k::item-2-properties::0"
    assert chunks[0]["company"] == "Apple"
    assert chunks[0]["year"] == 2025
    assert chunks[0]["document_type"] == "10-K"
    assert chunks[0]["section"] == "Item 2. Properties"
    assert chunks[0]["page"] is None


def test_paragraphs_never_split_across_chunks_unless_oversized():
    # 3 paragraphs of 300 tokens each = 900 tokens total, must split into 2+ chunks,
    # but each individual paragraph (300 < 500) must stay whole inside one chunk
    paragraphs = [_words(300), _words(300), _words(300)]
    sections = [{"section": "Item 1A. Risk Factors", "paragraphs": paragraphs}]
    chunks = chunk_sections(sections, **COMMON_KWARGS)

    assert len(chunks) > 1
    for paragraph in paragraphs:
        # every whole paragraph appears intact within exactly one chunk's text
        assert any(paragraph in c["chunk_text"] for c in chunks)


def test_last_paragraph_of_a_chunk_overlaps_into_the_next():
    paragraphs = [_words(300), _words(300), _words(300)]
    sections = [{"section": "Item 1A. Risk Factors", "paragraphs": paragraphs}]
    chunks = chunk_sections(sections, **COMMON_KWARGS)

    assert len(chunks) >= 2
    first_chunk_paragraphs = chunks[0]["chunk_text"].split("\n\n")
    second_chunk_paragraphs = chunks[1]["chunk_text"].split("\n\n")
    assert first_chunk_paragraphs[-1] == second_chunk_paragraphs[0]


def test_oversized_single_paragraph_is_token_sliced():
    huge_paragraph = _words(CHUNK_TOKENS * 2 + 10)
    sections = [{"section": "Item 8. Financial Statements and Supplementary Data", "paragraphs": [huge_paragraph]}]
    chunks = chunk_sections(sections, **COMMON_KWARGS)

    assert len(chunks) == 3  # 2 full-size pieces + 1 remainder
    for c in chunks[:-1]:
        assert len(_encoding.encode(c["chunk_text"])) == CHUNK_TOKENS


def test_chunk_ids_are_deterministic_across_runs():
    sections = [{"section": "Item 1. Business", "paragraphs": [_words(50)]}]
    first = chunk_sections(sections, **COMMON_KWARGS)
    second = chunk_sections(sections, **COMMON_KWARGS)
    assert [c["chunk_id"] for c in first] == [c["chunk_id"] for c in second]


def test_different_sections_produce_independently_indexed_chunk_ids():
    sections = [
        {"section": "Item 1. Business", "paragraphs": [_words(50)]},
        {"section": "Item 2. Properties", "paragraphs": [_words(50)]},
    ]
    chunks = chunk_sections(sections, **COMMON_KWARGS)
    ids = [c["chunk_id"] for c in chunks]
    assert "apple_2025_10-k::item-1-business::0" in ids
    assert "apple_2025_10-k::item-2-properties::0" in ids
