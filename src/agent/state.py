from typing import TypedDict


class AgentState(TypedDict):
    question: str
    use_hybrid: bool
    use_sql: bool
    sql_queries: list[dict]
    hybrid_results: list[dict]
    sql_results: list[dict | None]
    tool_calls: list[str]
    answer: str
