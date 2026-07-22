"""
Project 6 runner — batch mode.

Runs all 10 test requests with simulate_human="approve" (so it doesn't
block waiting for real input), and measures whether our trigger logic
correctly identifies which requests genuinely need human review, against
the expected_trigger labels in test_requests.py.

This is precision/recall on the TRIGGER decision, not on the refund
decision itself — we're testing "did we correctly identify risk," which is
the actual safety property this project is about.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.llm_client import LLMClient
from hitl_agent import process_request
from test_requests import REQUESTS


def run():
    client = LLMClient(provider="ollama", model="llama3.1")  # swap to LLMClient(provider="ollama", model="...") if desired
    true_pos = false_pos = true_neg = false_neg = 0

    for i, item in enumerate(REQUESTS):
        task_id = f"hitl-req{i}"
        _, triggered = process_request(item["text"], client, task_id, simulate_human="approve")
        expected = item["expected_trigger"]

        if triggered and expected:
            true_pos += 1
        elif triggered and not expected:
            false_pos += 1
        elif not triggered and not expected:
            true_neg += 1
        else:
            false_neg += 1

        match = "OK" if triggered == expected else "MISS"
        print(f"[{match}] req {i} | triggered={triggered} expected={expected}")

    total = len(REQUESTS)
    precision = true_pos / (true_pos + false_pos) if (true_pos + false_pos) else float("nan")
    recall = true_pos / (true_pos + false_neg) if (true_pos + false_neg) else float("nan")

    print(f"\n--- Trigger accuracy over {total} requests ---")
    print(f"True positives (correctly escalated): {true_pos}")
    print(f"False positives (escalated but shouldn't have): {false_pos}")
    print(f"True negatives (correctly auto-approved): {true_neg}")
    print(f"False negatives (SHOULD have escalated but didn't — the dangerous case): {false_neg}")
    print(f"Precision: {precision:.1%} | Recall: {recall:.1%}")


if __name__ == "__main__":
    run()
