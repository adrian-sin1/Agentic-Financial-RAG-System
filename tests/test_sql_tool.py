from unittest.mock import MagicMock, patch

from src.retrieval.sql_tool import query_financials


def _mock_connection(fetchone_return):
    cursor = MagicMock()
    cursor.fetchone.return_value = fetchone_return
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


def test_returns_none_when_no_row_matches():
    conn, cursor = _mock_connection(None)
    with patch("src.retrieval.sql_tool.get_snowflake_connection", return_value=conn):
        result = query_financials("Nonexistent Co", 1999, "revenue")
    assert result is None


def test_maps_row_columns_to_named_fields():
    row = ("Apple", 2025, "FY", "revenue", 416161000000.0, "USD", "SEC EDGAR XBRL (RevenueFromContract...)")
    conn, cursor = _mock_connection(row)
    with patch("src.retrieval.sql_tool.get_snowflake_connection", return_value=conn):
        result = query_financials("Apple", 2025, "revenue")

    assert result == {
        "company": "Apple",
        "year": 2025,
        "fiscal_period": "FY",
        "metric_name": "revenue",
        "metric_value": 416161000000.0,
        "unit": "USD",
        "source": "SEC EDGAR XBRL (RevenueFromContract...)",
    }


def test_query_is_parameterized_not_string_interpolated():
    """The company/year/metric values must never be spliced directly into the
    SQL text -- they must travel as separate bind parameters, so a value like
    Robert'); DROP TABLE financial_metrics;-- can never break out of the
    string literal and change what the query does.
    """
    conn, cursor = _mock_connection(None)
    malicious_company = "Apple'; DROP TABLE financial_metrics; --"
    with patch("src.retrieval.sql_tool.get_snowflake_connection", return_value=conn):
        query_financials(malicious_company, 2025, "revenue")

    args, kwargs = cursor.execute.call_args
    sql_text = args[0]
    bind_params = args[1]

    assert malicious_company not in sql_text
    assert "%s" in sql_text
    assert bind_params == (malicious_company, 2025, "revenue")


def test_connection_is_closed_even_on_the_no_match_path():
    conn, cursor = _mock_connection(None)
    with patch("src.retrieval.sql_tool.get_snowflake_connection", return_value=conn):
        query_financials("Apple", 2025, "revenue")
    conn.close.assert_called_once()


def test_colloquial_company_name_is_normalized_before_querying():
    """People say "Google", not "Alphabet" -- the router will pass through
    whatever the user said, so the lookup must normalize it or a perfectly
    valid question silently finds nothing.
    """
    conn, cursor = _mock_connection(None)
    with patch("src.retrieval.sql_tool.get_snowflake_connection", return_value=conn):
        query_financials("Google", 2025, "revenue")

    bind_params = cursor.execute.call_args[0][1]
    assert bind_params[0] == "Alphabet"
