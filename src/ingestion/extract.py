import re
import warnings

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

SECTION_HEADER_RE = re.compile(r"^Item\s+\d+[A-Z]?\.?\s*\S")


def extract_sections(html_path: str) -> list[dict]:
    """Parse a 10-K HTML filing into ordered {"section", "text"} blocks, one per
    Item (plus a leading "Cover Page" block for anything before Item 1).

    SEC filings are inline XBRL: the raw HTML embeds machine-readable XBRL facts
    inline via hidden (display:none) elements and an <ix:header> block. Those get
    stripped before extracting visible text, or they'd pollute every chunk.
    """
    with open(html_path, encoding="utf-8") as f:
        raw = f.read()

    soup = BeautifulSoup(raw, "lxml")

    for el in soup.find_all(style=lambda v: v and "display:none" in v.replace(" ", "")):
        el.decompose()
    header = soup.find("ix:header")
    if header:
        header.decompose()

    text = soup.get_text("\n")
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    sections = []
    current_section = "Cover Page"
    current_lines: list[str] = []
    for line in lines:
        normalized = re.sub(r"\s+", " ", line.replace("\xa0", " ")).strip()
        if SECTION_HEADER_RE.match(normalized):
            if current_lines:
                sections.append({"section": current_section, "text": "\n".join(current_lines)})
            current_section = normalized
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections.append({"section": current_section, "text": "\n".join(current_lines)})

    return sections
