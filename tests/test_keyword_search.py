from unittest.mock import MagicMock, patch

from src.retrieval.keyword_search import _keywords, _phrases, keyword_search


def test_keywords_drops_stopwords_and_short_tokens():
    assert _keywords("What is the capital of Mongolia?") == ["capital", "mongolia"]


def test_phrases_are_consecutive_keyword_bigrams():
    assert _phrases("legal proceedings against Apple") == ["legal proceedings", "proceedings against", "against apple"]


def test_returns_empty_list_when_question_has_no_real_keywords():
    with patch("src.retrieval.keyword_search.get_snowflake_connection") as mock_conn:
        results = keyword_search("What is it?")
    assert results == []
    mock_conn.assert_not_called()


def _mock_connection(rows):
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


def test_query_is_parameterized_not_string_interpolated():
    """User-derived keywords/phrases must travel as bind parameters, never
    spliced into the SQL text -- otherwise a crafted question could break out
    of the ILIKE string literal.
    """
    conn, cursor = _mock_connection([])
    malicious_question = "legal proceedings'; DROP TABLE document_chunks; --"
    with patch("src.retrieval.keyword_search.get_snowflake_connection", return_value=conn):
        keyword_search(malicious_question)

    sql_text = cursor.execute.call_args[0][0]
    assert "DROP TABLE" not in sql_text
    assert "%s" in sql_text


def test_company_filter_is_appended_as_a_parameter_when_given():
    conn, cursor = _mock_connection([])
    with patch("src.retrieval.keyword_search.get_snowflake_connection", return_value=conn):
        keyword_search("risk factors", company="Apple")

    sql_text, params = cursor.execute.call_args[0]
    assert "AND company = %s" in sql_text
    assert "Apple" in params


def test_phrase_matches_are_weighted_higher_than_single_keyword_matches():
    conn, cursor = _mock_connection([])
    with patch("src.retrieval.keyword_search.get_snowflake_connection", return_value=conn):
        keyword_search("legal proceedings")

    sql_text = cursor.execute.call_args[0][0]
    assert "IFF(chunk_text ILIKE %s, 3, 0)" in sql_text  # the phrase term
    assert "IFF(chunk_text ILIKE %s, 1, 0)" in sql_text  # the single-keyword terms


def test_maps_result_rows_to_named_fields():
    row = ("chunk1", "Apple", 2025, "10-K", "Item 1A. Risk Factors", None, "some text", 5)
    conn, cursor = _mock_connection([row])
    with patch("src.retrieval.keyword_search.get_snowflake_connection", return_value=conn):
        results = keyword_search("risk factors")

    assert results == [
        {
            "chunk_id": "chunk1",
            "company": "Apple",
            "year": 2025,
            "document_type": "10-K",
            "section": "Item 1A. Risk Factors",
            "page": None,
            "chunk_text": "some text",
            "match_count": 5,
        }
    ]
