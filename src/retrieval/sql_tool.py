from src.db.connection import get_snowflake_connection


def query_financials(company: str, year: int, metric: str) -> dict | None:
    """Constrained, parameterized lookup into financial_metrics -- intentionally
    NOT free-form LLM-generated SQL, so the agent can only ever read exactly
    one (company, year, metric) row.
    """
    conn = get_snowflake_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT company, year, fiscal_period, metric_name, metric_value, unit, source
        FROM financial_metrics
        WHERE company = %s AND year = %s AND metric_name = %s
        """,
        (company, year, metric),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        return None
    return {
        "company": row[0],
        "year": row[1],
        "fiscal_period": row[2],
        "metric_name": row[3],
        "metric_value": row[4],
        "unit": row[5],
        "source": row[6],
    }
