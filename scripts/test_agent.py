import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agent.graph import answer_question  # noqa: E402

CASES = {
    "unstructured-only": "What risks did Apple identify related to its supply chain in its 2025 10-K?",
    "structured-only": "What was Apple's diluted earnings per share for fiscal year 2025?",
    "combined": "Compare Apple's fiscal 2025 revenue growth and the risks it faces -- give me the net income figure and a cited risk.",
    "no-match": "What is the capital of Mongolia and how many llamas live there?",
}


def main():
    for label, question in CASES.items():
        print(f"\n{'=' * 70}\n[{label}] {question}\n{'=' * 70}")
        result = answer_question(question)
        print("tools called:", result["tool_calls"])
        print("\nanswer:\n", result["answer"])


if __name__ == "__main__":
    main()
