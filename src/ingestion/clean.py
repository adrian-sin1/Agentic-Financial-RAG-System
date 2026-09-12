import re

MIN_SECTION_CHARS = 200


def clean_sections(sections: list[dict]) -> list[dict]:
    """Collapse whitespace and drop sections too short to carry real content
    (table-of-contents entries, "[Reserved]" placeholders, empty items)."""
    cleaned = []
    for s in sections:
        text = re.sub(r"[ \t]+", " ", s["text"])
        text = re.sub(r"\n{2,}", "\n", text).strip()
        if len(text) < MIN_SECTION_CHARS:
            continue
        cleaned.append({"section": s["section"], "text": text})
    return cleaned
