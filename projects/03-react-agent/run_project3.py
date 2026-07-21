"""
Project 3 runner. Runs every task through the ReAct loop, extracts a number
from the final answer, and checks it against the known-correct value.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.llm_client import LLMClient
from react_agent import run_agent
from test_tasks import TASKS


def extract_number(text: str):
    matches = re.findall(r"-?\d+\.?\d*", text)
    return float(matches[-1]) if matches else None


def run():
    client = LLMClient(provider="ollama", model="llama3.1")  # swap to LLMClient(provider="ollama", model="llama3.1") to run free
    correct = 0
    capped = 0

    for i, item in enumerate(TASKS):
        task_id = f"task{i}"
        answer_text, iterations, hit_cap = run_agent(item["task"], client, task_id)
        got = extract_number(answer_text)
        is_correct = got is not None and abs(got - item["expected"]) <= item["tolerance"]

        correct += int(is_correct)
        capped += int(hit_cap)

        status = "OK " if is_correct else "MISS"
        cap_flag = " (hit cap)" if hit_cap else ""
        print(
            f"[{status}] task {i} | {iterations} steps{cap_flag} | "
            f"got={got} expected={item['expected']:.2f} | \"{item['task'][:60]}...\""
        )

    print(f"\n{correct}/{len(TASKS)} correct. {capped}/{len(TASKS)} hit the iteration cap.")


if __name__ == "__main__":
    run()
