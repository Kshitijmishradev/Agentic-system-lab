"""
HITL tree navigator for the relay config.

Triggers only when the relay result is untrustworthy — no clean version, OR
the clean versions DISAGREE with each other (the real danger case: confident
wrong answers that each ran fine). On trigger, it shows the human the full
refinement tree and lets them:

  <number>  rewind to that version and relay one more step from it (branch)
  e         hand-write / paste a corrected SQL and run it
  a <number> accept a specific version as the final answer
  q         accept the current best as-is

Every human action is logged as an audit trail entry.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.llm_client import LLMClient
from core.schemas import generate_structured
from core.tracing import log_span

from config import MODELS, SCHEMA_DESCRIPTION
from sql_tool import run_sql
from query_tree import QueryTree
from relay_config import SQLProposal, _run_and_summarize


def needs_review(tree: QueryTree) -> tuple[bool, str]:
    """Trigger logic — our own code decides, not a model."""
    ok_versions = [v for v in tree.versions if v.ran_ok]
    if not ok_versions:
        return True, "no query ran successfully"

    # Compare the actual returned rows of the successful versions. If they
    # disagree, we have confident-but-conflicting answers — exactly when a
    # human should look.
    distinct_results = {str(v.rows) for v in ok_versions}
    if len(distinct_results) > 1:
        return True, f"{len(distinct_results)} different answers across successful queries — they disagree"
    return False, "all successful queries agree"


def _relay_one_step_from(tree: QueryTree, parent_id: int, question: str, task_id: str):
    """Branch: ask a model to improve a chosen version, add as a new node."""
    parent = tree.get(parent_id)
    improver = MODELS[len(tree.versions) % len(MODELS)]
    prompt = (
        f"Question: {question}\n\nPrevious SQL:\n{parent.sql}\n\n"
        f"Result: {parent.result_summary}\n\nImprove this query to correctly answer the question."
    )
    client = LLMClient(provider="ollama", model=improver)
    try:
        improved = generate_structured(client, prompt, SQLProposal, max_retries=2,
                                       task_id=task_id, system=SCHEMA_DESCRIPTION)
        ok, rows, summary = _run_and_summarize(improved.sql_query)
        return tree.add(parent.id, improver, improved.sql_query, ok, summary, rows)
    except Exception as e:
        return tree.add(parent.id, improver, "(failed to generate)", False, str(e)[:80])


def review_tree(tree: QueryTree, question: str, task_id: str = "hitl-review") -> int:
    """Interactive review. Returns the version id the human settled on."""
    triggered, reason = needs_review(tree)
    if not triggered:
        best = tree.best_ok_version()
        return best.id if best else 0

    print(f"\n{'!'*60}")
    print(f"HUMAN REVIEW NEEDED: {reason}")
    print(f"Question: {question}")
    print('!'*60)

    while True:
        print("\nCurrent refinement tree:\n")
        print(tree.render())
        print("\nOptions:")
        print("  <number>    rewind to that version and try one more improvement from it")
        print("  e           write/paste your own corrected SQL")
        print("  a <number>  accept that version as the final answer")
        print("  q           accept the current best runnable version as-is")

        choice = input("\nyour move ▸ ").strip()

        if choice == "q":
            best = tree.best_ok_version()
            final_id = best.id if best else 0
            _log(task_id, question, "accept_best_as_is", final_id)
            return final_id

        if choice.startswith("a "):
            try:
                final_id = int(choice.split()[1])
                tree.get(final_id)  # validate it exists
                _log(task_id, question, "accept_specific_version", final_id)
                return final_id
            except (ValueError, IndexError):
                print("  (couldn't parse — try 'a 2')")
                continue

        if choice == "e":
            user_sql = input("paste your SQL ▸ ").strip()
            ok, rows, summary = _run_and_summarize(user_sql)
            # human edits branch off the current best (or root if none)
            best = tree.best_ok_version()
            parent_id = best.id if best else (tree.versions[0].id if tree.versions else None)
            new_id = tree.add(parent_id, "human", user_sql, ok, summary, rows)
            print(f"  → ran your SQL: {summary}")
            _log(task_id, question, "human_edited_sql", new_id)
            continue

        # otherwise: treat as a version number to rewind + branch from
        try:
            rewind_id = int(choice)
            tree.get(rewind_id)
            new_id = _relay_one_step_from(tree, rewind_id, question, f"{task_id}-branch")
            print(f"  → branched from v{rewind_id}, created v{new_id}")
            _log(task_id, question, f"rewind_branch_from_v{rewind_id}", new_id)
        except (ValueError, IndexError):
            print("  (didn't understand — enter a number, 'e', 'a <n>', or 'q')")


def _log(task_id, question, action, version_id):
    log_span(task_id=task_id, kind="hitl_tree_action", input_summary=question[:200],
             output_summary=f"{action} -> v{version_id}", latency_s=0, cost_usd=0,
             tokens={}, success=True, extra={"action": action, "chosen_version": version_id})
