"""
Quick hands-on test: run the relay on ONE question and print the resulting
query tree. This is just to SEE the version chain build up on real data
before we add the HITL navigator on top. Not part of the eval.

Run:  python test_relay.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from relay_config import relay_answer
from hitl_review import review_tree

QUESTION = "Which team has scored the most total goals across all seasons, counting both home and away goals?"

if __name__ == "__main__":
    print(f"Question: {QUESTION}\n")
    print("Running relay (this takes a bit — several models in sequence)...\n")

    tree = relay_answer(QUESTION, task_id="test-relay")

    print("=" * 60)
    print("QUERY REFINEMENT TREE")
    print("=" * 60)
    print(tree.render())
    print("=" * 60)

    # HITL: if the versions disagree or none ran, this pauses for you to
    # navigate the tree. If they agree, it returns the best automatically.
    final_id = review_tree(tree, QUESTION)
    final = tree.get(final_id)
    print(f"\nFinal chosen version: v{final.id} (by {final.model})")
    print(f"SQL: {final.sql}")
    print(f"Result: {final.result_summary}")
    if final.rows:
        print(f"Answer: {final.rows[:3]}")