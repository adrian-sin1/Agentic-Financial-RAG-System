from src.ingestion.extract import extract_sections

SAMPLE_HTML = """
<html>
<body>
<ix:header><div>xbrl context junk that must never appear in output</div></ix:header>
<div style="display:none">hidden xbrl fact that must never appear in output</div>
<div style="margin-top:6pt"><span>Item 1.</span><span>&#160;&#160;&#160;&#160;Business</span></div>
<div style="margin-top:6pt">
  <span>The Company designs </span><span>iPhone</span><span>&#174;</span><span> and other products.</span>
</div>
<div style="margin-top:6pt"><span>Item 1A.</span><span>&#160;&#160;&#160;&#160;Risk Factors</span></div>
<div style="margin-top:6pt"><span>There are many risks to our business that could harm results.</span></div>
</body>
</html>
"""


def _write_html(tmp_path, content=SAMPLE_HTML):
    path = tmp_path / "filing.htm"
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_strips_hidden_and_xbrl_header_content(tmp_path):
    sections = extract_sections(_write_html(tmp_path))
    all_text = " ".join(p for s in sections for p in s["paragraphs"]) + " " + " ".join(
        s["section"] for s in sections
    )
    assert "junk" not in all_text


def test_splits_into_item_sections(tmp_path):
    sections = extract_sections(_write_html(tmp_path))
    section_names = [s["section"] for s in sections]
    assert any(name.startswith("Item 1.") for name in section_names)
    assert any(name.startswith("Item 1A.") for name in section_names)


def test_reconstructs_paragraph_split_across_inline_spans(tmp_path):
    sections = extract_sections(_write_html(tmp_path))
    business = next(s for s in sections if s["section"].startswith("Item 1."))
    # the sentence was split across 4 separate <span> tags in the source HTML;
    # extract_sections should reconstruct it as one continuous paragraph
    assert any("iPhone" in p and "and other products" in p for p in business["paragraphs"])


def test_content_before_first_item_becomes_cover_page(tmp_path):
    html = '<html><body><div style="margin-top:6pt"><span>Some cover page text.</span></div></body></html>'
    sections = extract_sections(_write_html(tmp_path, html))
    assert sections[0]["section"] == "Cover Page"
    assert "Some cover page text." in sections[0]["paragraphs"]
