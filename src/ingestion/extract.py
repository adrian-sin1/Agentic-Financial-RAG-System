import re
import warnings

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

SECTION_HEADER_RE = re.compile(r"^Item\s+\d+[A-Z]?\.?\s*\S")
MAX_HEADER_LEN = 150


def _is_leaf_block(tag) -> bool:
    """A paragraph-level container: a div/p with no nested block-level
    descendants (div/p/table) -- just inline formatting runs (span, b, sup,
    etc). This is what actually delimits one paragraph in these filings --
    each paragraph is its own <div>, with inline spans inside it for bold
    text, trademark symbols, and similar formatting runs.
    """
    return tag.name in ("div", "p") and tag.find(["div", "p", "table"]) is None


def _extract_blocks(soup) -> list[str]:
    """Walk the document in order, returning one string per paragraph/table
    block. Paragraph text is joined with spaces (not newlines) so inline
    formatting spans don't fracture one sentence into several pieces --
    e.g. "iPhone" + a separately-styled "(R)" + "is the Company's line of
    smartphones..." are all one <div> and become one reconstructed sentence.
    """
    blocks = []
    for tag in soup.find_all(["div", "p", "table"]):
        if tag.find_parent("table") is not None:
            continue  # already covered by an ancestor table, or nested table
        if tag.name == "table":
            text = tag.get_text("\n").strip()
        elif _is_leaf_block(tag):
            text = re.sub(r"\s+", " ", tag.get_text(" ")).strip()
        else:
            continue
        if text:
            blocks.append(text)
    return blocks


def extract_sections(html_path: str) -> list[dict]:
    """Parse a 10-K HTML filing into ordered {"section", "paragraphs"} blocks,
    one per Item (plus a leading "Cover Page" block for anything before Item 1).
    Each section's "paragraphs" is a list of paragraph/table-level text
    blocks -- preserving document structure for paragraph-aware chunking,
    instead of one flat blob of text per section.

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

    blocks = _extract_blocks(soup)

    sections = []
    current_section = "Cover Page"
    current_paragraphs: list[str] = []
    for block in blocks:
        normalized = re.sub(r"\s+", " ", block.replace("\xa0", " ")).strip()
        if len(normalized) < MAX_HEADER_LEN and SECTION_HEADER_RE.match(normalized):
            if current_paragraphs:
                sections.append({"section": current_section, "paragraphs": current_paragraphs})
            current_section = normalized
            current_paragraphs = []
        else:
            current_paragraphs.append(block)
    if current_paragraphs:
        sections.append({"section": current_section, "paragraphs": current_paragraphs})

    return sections
