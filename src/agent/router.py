import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

ROUTER_MODEL = "gpt-4o-mini"
VALID_METRICS = ["revenue", "net_income", "total_assets", "eps_diluted"]

ROUTER_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "router_decision",
        "schema": {
            "type": "object",
            "properties": {
                "use_hybrid_search": {"type": "boolean"},
                "hybrid_search_company": {"type": ["string", "null"]},
                "use_sql_tool": {"type": "boolean"},
                "sql_queries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "company": {"type": "string"},
                            "year": {"type": "integer"},
                            "metric": {"type": "string", "enum": VALID_METRICS},
                        },
                        "required": ["company", "year", "metric"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["use_hybrid_search", "hybrid_search_company", "use_sql_tool", "sql_queries"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}

ROUTER_SYSTEM_PROMPT = f"""You are the routing component of a financial research assistant. Decide which \
data sources are needed to answer the user's question about SEC filings.

- use_hybrid_search: true if the question needs qualitative/narrative information from a 10-K \
(business description, risk factors, legal proceedings, MD&A, controls, etc.)
- hybrid_search_company: if use_hybrid_search is true AND the question is clearly about ONE specific \
company, put that company's name here so the search only looks at that company's filings (the index \
holds multiple companies' filings together, and an unfiltered search can surface another company's \
similarly-worded risk factors instead of the one actually asked about). Set this to null if \
use_hybrid_search is false, or if the question genuinely spans/compares multiple companies, or names \
none.
- use_sql_tool: true if the question needs an exact structured financial figure. Valid metric names \
are exactly: {", ".join(VALID_METRICS)}.

If use_sql_tool is true, populate sql_queries with one entry per (company, year, metric) triple \
needed -- infer the company name and fiscal year from the question. A question can need both tools \
at once (e.g. "what was Apple's net income, and what risks does it face?").

If the question is unrelated to any company's filings or financials (small talk, unrelated trivia), \
set both flags to false and leave sql_queries empty.
"""


def route(question: str) -> dict:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=ROUTER_MODEL,
        messages=[
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        response_format=ROUTER_SCHEMA,
    )
    return json.loads(response.choices[0].message.content)
