import re

MIN_SECTION_CHARS = 200


def clean_sections(sections: list[dict]) -> list[dict]:
    """Collapse whitespace within each paragraph and drop sections too short
    to carry real content ("[Reserved]" placeholders, empty items)."""
    cleaned = []
    for s in sections:
        paragraphs = [re.sub(r"[ \t]+", " ", p).strip() for p in s["paragraphs"]]
        paragraphs = [p for p in paragraphs if p]
        if sum(len(p) for p in paragraphs) < MIN_SECTION_CHARS:
            continue
        cleaned.append({"section": s["section"], "paragraphs": paragraphs})
    return cleaned
