import argparse

import requests

from src.db.connection import get_snowflake_connection

SEC_USER_AGENT = "123bozobob@gmail.com Financial RAG portfolio project"

# SEC XBRL tags vary by metric and sometimes by era (e.g. companies switched from
# "Revenues" to "RevenueFromContractWithCustomerExcludingAssessedTax" around the
# 2018 revenue-recognition standard change). List candidates in preference order;
# the first tag with data for the requested fiscal year wins.
METRIC_TAGS = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ],
    "net_income": ["NetIncomeLoss"],
    "total_assets": ["Assets"],
    "eps_diluted": ["EarningsPerShareDiluted"],
}


def fetch_companyfacts(cik: str) -> dict:
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    resp = requests.get(url, headers={"User-Agent": SEC_USER_AGENT}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def extract_annual_metric(facts: dict, tags: list[str], year: int) -> dict | None:
    """Find the annual (fp="FY", form="10-K") value for the first tag in `tags`
    that has one for `year`.

    SEC's XBRL "fy" field marks which filing's fiscal year a fact was reported
    under, NOT which period it covers -- every 10-K reports 3 comparative years
    (current + 2 prior), all tagged with the SAME fy label as the filing itself.
    So filtering on fy alone returns 3 candidates; the actual current-year fact
    is always the one with the latest period end date among them (prior-year
    comparatives necessarily end earlier).
    """
    gaap = facts.get("facts", {}).get("us-gaap", {})
    for tag in tags:
        concept = gaap.get(tag)
        if not concept:
            continue
        for unit, points in concept.get("units", {}).items():
            candidates = [
                p
                for p in points
                if p.get("fy") == year and p.get("fp") == "FY" and p.get("form", "").startswith("10-K")
            ]
            if not candidates:
                continue
            best = max(candidates, key=lambda p: p.get("end", ""))
            return {"value": best["val"], "unit": unit, "tag": tag}
    return None


def extract_financials(company: str, cik: str, year: int) -> list[dict]:
    facts = fetch_companyfacts(cik)
    rows = []
    for metric_name, tags in METRIC_TAGS.items():
        result = extract_annual_metric(facts, tags, year)
        if result is None:
            continue
        rows.append(
            {
                "metric_id": f"{company.lower()}_{year}_{metric_name}",
                "company": company,
                "year": year,
                "fiscal_period": "FY",
                "metric_name": metric_name,
                "metric_value": result["value"],
                "unit": result["unit"],
                "source": f"SEC EDGAR XBRL ({result['tag']})",
            }
        )
    return rows


def load_financials(rows: list[dict]):
    conn = get_snowflake_connection()
    cur = conn.cursor()
    cur.executemany(
        """
        MERGE INTO financial_metrics t
        USING (SELECT %(metric_id)s AS metric_id) s
        ON t.metric_id = s.metric_id
        WHEN MATCHED THEN UPDATE SET
            company = %(company)s, year = %(year)s, fiscal_period = %(fiscal_period)s,
            metric_name = %(metric_name)s, metric_value = %(metric_value)s,
            unit = %(unit)s, source = %(source)s
        WHEN NOT MATCHED THEN INSERT
            (metric_id, company, year, fiscal_period, metric_name, metric_value, unit, source)
        VALUES
            (%(metric_id)s, %(company)s, %(year)s, %(fiscal_period)s, %(metric_name)s,
             %(metric_value)s, %(unit)s, %(source)s)
        """,
        rows,
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pull annual financial metrics from SEC EDGAR XBRL into Snowflake")
    parser.add_argument("--company", required=True)
    parser.add_argument("--cik", required=True, help="10-digit CIK, e.g. 0000320193")
    parser.add_argument("--year", required=True, type=int)
    args = parser.parse_args()

    metric_rows = extract_financials(args.company, args.cik, args.year)
    load_financials(metric_rows)
    print(f"Loaded {len(metric_rows)} metrics for {args.company} {args.year}")
    for row in metric_rows:
        print(f"  {row['metric_name']}: {row['metric_value']} {row['unit']}")
