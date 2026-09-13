import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.retrieval.hybrid_search import hybrid_search  # noqa: E402
from src.retrieval.sql_tool import query_financials  # noqa: E402

GOLDEN_PATH = os.path.join(os.path.dirname(__file__), "golden_questions.jsonl")
PASS_THRESHOLD = 0.8


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


def main():
    items = load_golden()
    passed = 0
    for item in items:
        ok = evaluate(item)
        passed += ok
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] ({item['type']}) {item['question']}")

    score = passed / len(items)
    print(f"\n{passed}/{len(items)} passed ({score:.0%})")

    if score < PASS_THRESHOLD:
        print(f"Below pass threshold of {PASS_THRESHOLD:.0%}")
        sys.exit(1)


if __name__ == "__main__":
    main()
