"""
Evaluation harness — the part that proves the reliability claim with real
numbers. Runs every ground-truth question two ways and compares accuracy:

  - single model alone (MODELS[0]): baseline
  - full debate (3 models + critic + self-heal): the product

The gap between them is the answer to "does the multi-agent debate actually
make this more reliable, or is it just extra cost?" — measured, not assumed.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.llm_client import LLMClient
from core.schemas import generate_structured

from config import MODELS, SCHEMA_DESCRIPTION
from sql_tool import run_sql, format_rows
from debate_engine import answer_question, SQLProposal
from test_questions import QUESTIONS


def check(text: str, expected, check_type: str, tol: float = 0) -> bool:
    if text is None:
        return False
    if check_type == "contains":
        return str(expected).lower() in text.lower()
    if check_type == "numeric":
        nums = re.findall(r"-?\d[\d,]*\.?\d*", text)
        for n in nums:
            try:
                if abs(float(n.replace(",", "")) - float(expected)) <= tol:
                    return True
            except ValueError:
                continue
        return False
    return False


def single_model_answer(question: str, task_id: str):
    """Baseline: one model writes SQL, we run it, return the raw result text.
    No critic, no debate, no self-heal."""
    try:
        client = LLMClient(provider="ollama", model=MODELS[0])
        proposal = generate_structured(
            client, f"Question: {question}", SQLProposal, max_retries=2,
            task_id=task_id, system=SCHEMA_DESCRIPTION,
        )
        ok, rows, msg = run_sql(proposal.sql_query)
        return format_rows(rows) if ok else None
    except Exception:
        return None


def run():
    single_correct = 0
    debate_correct = 0

    for i, item in enumerate(QUESTIONS):
        q = item["question"]
        print(f"\nQ{i}: {q}")

        single = single_model_answer(q, f"eval-single-q{i}")
        single_ok = check(single, item["expected"], item["check"], item.get("tolerance", 0))
        single_correct += int(single_ok)

        result = answer_question(q, task_id=f"eval-debate-q{i}")
        debate_ok = check(result.final_answer, item["expected"], item["check"], item.get("tolerance", 0))
        debate_correct += int(debate_ok)

        print(f"    expected: {item['expected']}")
        print(f"    single-model: {'OK' if single_ok else 'MISS'}  |  "
              f"debate: {'OK' if debate_ok else 'MISS'} "
              f"(conf={result.confidence}, {result.agreement_level}"
              f"{', healed' if result.healed else ''})")

    total = len(QUESTIONS)
    print(f"\n{'='*50}")
    print(f"Single model ({MODELS[0]}) alone: {single_correct}/{total} correct ({single_correct/total:.0%})")
    print(f"Full debate (3 models + critic):  {debate_correct}/{total} correct ({debate_correct/total:.0%})")
    print(f"{'='*50}")


if __name__ == "__main__":
    run()
