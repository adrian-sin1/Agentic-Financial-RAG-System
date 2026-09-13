from src.ingestion.clean import MIN_SECTION_CHARS, clean_sections


def test_drops_sections_below_min_length():
    sections = [
        {"section": "Item 6. [Reserved]", "paragraphs": ["[Reserved]"]},
        {"section": "Item 1A. Risk Factors", "paragraphs": ["x" * MIN_SECTION_CHARS]},
    ]
    cleaned = clean_sections(sections)
    names = [s["section"] for s in cleaned]
    assert "Item 6. [Reserved]" not in names
    assert "Item 1A. Risk Factors" in names


def test_collapses_repeated_whitespace_within_a_paragraph():
    sections = [{"section": "Item 1. Business", "paragraphs": ["word1    word2\t\tword3" + "x" * MIN_SECTION_CHARS]}]
    cleaned = clean_sections(sections)
    assert "word1 word2 word3" in cleaned[0]["paragraphs"][0]


def test_drops_empty_paragraphs_after_stripping():
    sections = [{"section": "Item 1. Business", "paragraphs": ["   ", "x" * MIN_SECTION_CHARS, ""]}]
    cleaned = clean_sections(sections)
    assert cleaned[0]["paragraphs"] == ["x" * MIN_SECTION_CHARS]


def test_section_at_exactly_the_threshold_is_kept():
    sections = [{"section": "Item 1. Business", "paragraphs": ["x" * MIN_SECTION_CHARS]}]
    cleaned = clean_sections(sections)
    assert len(cleaned) == 1


def test_section_one_under_the_threshold_is_dropped():
    sections = [{"section": "Item 1. Business", "paragraphs": ["x" * (MIN_SECTION_CHARS - 1)]}]
    cleaned = clean_sections(sections)
    assert cleaned == []
