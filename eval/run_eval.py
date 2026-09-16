import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agent.router import route  # noqa: E402
from src.retrieval.hybrid_search import hybrid_search  # noqa: E402
from src.retrieval.sql_tool import query_financials  # noqa: E402

GOLDEN_PATH = os.path.join(os.path.dirname(__file__), "golden_questions.jsonl")
PASS_THRESHOLD = 0.8
ROUTING_PASS_THRESHOLD = 0.8

# Which tools the router should pick for each question type, derived from the
# same "type" field the retrieval checks already use -- no separate schema needed.
EXPECTED_TOOLS = {
    "structured": {"use_sql_tool": True, "use_hybrid_search": False},
    "unstructured": {"use_sql_tool": False, "use_hybrid_search": True},
    "combined": {"use_sql_tool": True, "use_hybrid_search": True},
    "no_match": {"use_sql_tool": False, "use_hybrid_search": False},
}


def load_golden() -> list[dict]:
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def check_structured(item: dict) -> bool:
    result = query_financials(**item["metric"])
    if result is None:
        return False
    expected = item["expected_value"]
    return abs(result["metric_value"] - expected) < max(abs(expected) * 0.001, 0.01)


def check_unstructured(item: dict) -> bool:
    results = hybrid_search(item["question"], top_k=5)
    sections = [r["section"] for r in results]
    return any(any(exp in sec for sec in sections) for exp in item["expected_sections"])


def check_no_match(item: dict) -> bool:
    return hybrid_search(item["question"], top_k=5) == []


def evaluate(item: dict) -> bool:
    qtype = item["type"]
    if qtype == "structured":
        return check_structured(item)
    if qtype == "unstructured":
        return check_unstructured(item)
    if qtype == "combined":
        return check_structured(item) and check_unstructured(item)
    if qtype == "no_match":
        return check_no_match(item)
    raise ValueError(f"Unknown question type: {qtype}")


def check_routing(item: dict) -> bool:
    """Does the LangGraph router pick the right tool(s) for this question, not
    just whether the underlying retrieval/SQL calls return the right data?
    Calls route() directly rather than the full answer_question() graph so
    this stays cheap (no synthesis LLM call).
    """
    decision = route(item["question"])
    expected = EXPECTED_TOOLS[item["type"]]
    return decision["use_sql_tool"] == expected["use_sql_tool"] and decision["use_hybrid_search"] == expected["use_hybrid_search"]


def main():
    items = load_golden()
    passed = 0
    routing_passed = 0
    for item in items:
        ok = evaluate(item)
        passed += ok
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] ({item['type']}) {item['question']}")

        routing_ok = check_routing(item)
        routing_passed += routing_ok
        routing_status = "PASS" if routing_ok else "FAIL"
        print(f"  [routing {routing_status}]")

    score = passed / len(items)
    routing_score = routing_passed / len(items)
    print(f"\nRetrieval/SQL accuracy: {passed}/{len(items)} passed ({score:.0%})")
    print(f"Router tool-selection accuracy: {routing_passed}/{len(items)} passed ({routing_score:.0%})")

    failed = False
    if score < PASS_THRESHOLD:
        print(f"Retrieval/SQL accuracy below pass threshold of {PASS_THRESHOLD:.0%}")
        failed = True
    if routing_score < ROUTING_PASS_THRESHOLD:
        print(f"Router tool-selection accuracy below pass threshold of {ROUTING_PASS_THRESHOLD:.0%}")
        failed = True

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
