"""
Experiment harness — the research result.

Runs all THREE agent architectures, fully autonomous (no human), on the same
9 verified ground-truth questions, and measures each on three axes:
  - accuracy  : did the final answer match verified ground truth?
  - latency   : wall-clock seconds per question
  - cost      : total tokens consumed (proxy for compute; $ on hosted models)

Configs:
  [A] single   : one model writes SQL, execute, done. No critic, no relay.
  [B] debate   : 3 models write SQL, critic judges from real results.
  [C] relay    : draft -> improve -> improve (bounded), auto-pick best version.
                 HITL disabled here so all three compete on equal footing —
                 the human-review layer is a separate product feature, not
                 part of the autonomous benchmark.

Run:  python run_experiment.py
Then the printed accuracy gap is the number for the resume bullet.
"""

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.llm_client import LLMClient
from core.schemas import generate_structured
from core.tracing import load_spans

from config import MODELS, SCHEMA_DESCRIPTION
from sql_tool import run_sql, format_rows
from debate_engine import answer_question, SQLProposal
from relay_config import relay_answer
from test_questions import QUESTIONS


def check(text, expected, check_type, tol=0):
    if text is None:
        return False
    if check_type == "contains":
        return str(expected).lower() in text.lower()
    if check_type == "numeric":
        for n in re.findall(r"-?\d[\d,]*\.?\d*", text):
            try:
                if abs(float(n.replace(",", "")) - float(expected)) <= tol:
                    return True
            except ValueError:
                pass
        return False
    return False


def tokens_since(marker_index):
    """Sum tokens from llm_call spans logged after a given span-count marker."""
    spans = load_spans(kind="llm_call")
    recent = spans[marker_index:]
    return sum(s["tokens"].get("input", 0) + s["tokens"].get("output", 0) for s in recent)


# --- config runners: each returns (answer_text, is_correct-able text) ---

def run_single(question, task_id):
    try:
        client = LLMClient(provider="ollama", model=MODELS[0])
        proposal = generate_structured(client, f"Question: {question}", SQLProposal,
                                        max_retries=2, task_id=task_id, system=SCHEMA_DESCRIPTION)
        ok, rows, msg = run_sql(proposal.sql_query)
        return format_rows(rows) if ok else None
    except Exception:
        return None


def run_debate(question, task_id):
    result = answer_question(question, task_id=task_id)
    return result.final_answer


def run_relay(question, task_id):
    tree = relay_answer(question, task_id=task_id)
    best = tree.best_ok_version()
    return format_rows(best.rows) if best and best.rows else None


CONFIGS = {
    "single": run_single,
    "debate": run_debate,
    "relay":  run_relay,
}


def run():
    # stats[config] = {correct, total_latency, total_tokens}
    stats = {name: {"correct": 0, "latency": 0.0, "tokens": 0} for name in CONFIGS}

    for i, item in enumerate(QUESTIONS):
        q = item["question"]
        print(f"\nQ{i}: {q[:65]}...")
        for name, fn in CONFIGS.items():
            token_marker = len(load_spans(kind="llm_call"))
            t0 = time.time()
            answer = fn(q, f"exp-{name}-q{i}")
            elapsed = time.time() - t0
            toks = tokens_since(token_marker)

            correct = check(answer, item["expected"], item["check"], item.get("tolerance", 0))
            stats[name]["correct"] += int(correct)
            stats[name]["latency"] += elapsed
            stats[name]["tokens"] += toks
            print(f"    {name:8} {'OK ' if correct else 'MISS'}  {elapsed:5.1f}s  {toks:5d} tok")

    total = len(QUESTIONS)
    print("\n" + "=" * 60)
    print(f"{'CONFIG':<10}{'ACCURACY':<14}{'AVG LATENCY':<14}{'AVG TOKENS':<12}")
    print("-" * 60)
    for name, s in stats.items():
        acc = s["correct"] / total
        print(f"{name:<10}{s['correct']}/{total} ({acc:.0%})   "
              f"{s['latency']/total:>6.1f}s      {s['tokens']//total:>6d}")
    print("=" * 60)
    print("\nThe accuracy column is your resume number. Note which config wins")
    print("on accuracy vs which is cheapest/fastest — that tradeoff IS the finding.")


if __name__ == "__main__":
    run()
