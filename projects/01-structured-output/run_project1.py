"""
Project 1 runner.

Runs every ticket through generate_structured() twice:
  - baseline: max_retries=1 (no correction loop — this is your "before")
  - improved: max_retries=3 (full retry-on-error loop — this is your "after")

Each run logs to logs/spans.jsonl with a distinct task_id so eval.py can
tell them apart. Run this, then run `python -m core.eval` to see the stats.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # repo root on path

from core.llm_client import LLMClient
from core.schemas import generate_structured
from ticket_schema import TicketTriage
from test_tickets import TICKETS

PROMPT_TEMPLATE = "Triage this customer support ticket:\n\n\"{ticket}\""


def run(max_retries: int, label: str):
    client = LLMClient(provider="ollama", model="llama3.1")
    successes = 0
    for i, ticket in enumerate(TICKETS):
        task_id = f"{label}-{i}"
        prompt = PROMPT_TEMPLATE.format(ticket=ticket)
        try:
            result = generate_structured(
                client, prompt, TicketTriage, max_retries=max_retries, task_id=task_id
            )
            successes += 1
            print(f"[{label}] #{i} OK  -> {result.category}/{result.priority}")
        except Exception as e:
            print(f"[{label}] #{i} FAIL -> {str(e)[:100]}")
    print(f"\n{label}: {successes}/{len(TICKETS)} succeeded\n")


if __name__ == "__main__":
    print("=== BASELINE (max_retries=1, no correction loop) ===")
    run(max_retries=1, label="baseline")

    print("=== IMPROVED (max_retries=3, correction loop enabled) ===")
    run(max_retries=3, label="improved")
