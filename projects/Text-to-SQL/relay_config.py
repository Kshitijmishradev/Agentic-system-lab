"""
Config [C] — Relay refinement.

One model drafts a query; the next model tries to IMPROVE it; repeat, up to
a cap. Every attempt is added to the QueryTree as a node. Bounded loop with
an execution-based stop rule (Project 3's pattern applied to SQL):
stop when a query runs cleanly AND a critic judges it sound, or at the cap.

The runtime stop rule ("runs clean + critic approves") is a HEURISTIC — it
can't see ground truth. The eval measures separately whether that heuristic
actually correlated with correctness. Keeping those two apart is the honest
part of the study.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pydantic import BaseModel
from typing import Literal

from core.llm_client import LLMClient
from core.schemas import generate_structured
from core.tracing import log_span

from config import MODELS, SCHEMA_DESCRIPTION
from sql_tool import run_sql, format_rows
from query_tree import QueryTree

MAX_RELAY_STEPS = 4


class SQLProposal(BaseModel):
    sql_query: str
    reasoning: str


class RefinementJudge(BaseModel):
    is_good_enough: bool     # is this query sound and complete for the question?
    reason: str


def _run_and_summarize(sql: str):
    ok, rows, msg = run_sql(sql)
    if ok:
        summary = f"{len(rows)} rows" if rows else "0 rows"
    else:
        summary = msg
    return ok, rows, summary


def relay_answer(question: str, task_id: str = "relay") -> QueryTree:
    tree = QueryTree()

    # --- v0: first model drafts from scratch ---
    drafter = MODELS[0]
    client = LLMClient(provider="ollama", model=drafter)
    try:
        draft = generate_structured(
            client, f"Question: {question}", SQLProposal, max_retries=2,
            task_id=f"{task_id}-draft", system=SCHEMA_DESCRIPTION,
        )
        ok, rows, summary = _run_and_summarize(draft.sql_query)
        current_id = tree.add(None, drafter, draft.sql_query, ok, summary, rows)
    except Exception as e:
        # Even the first draft failed — record it and return the tree as-is.
        tree.add(None, drafter, "(failed to generate a valid query)",
                 False, f"generation error: {str(e)[:100]}")
        return tree

    # --- refinement relay: each subsequent model improves the current best ---
    for step in range(1, MAX_RELAY_STEPS):
        improver = MODELS[step % len(MODELS)]  # rotate through models
        current = tree.get(current_id)

        improve_prompt = (
            f"Question: {question}\n\n"
            f"A previous model wrote this SQL:\n{current.sql}\n\n"
            f"When executed it gave: {current.result_summary}\n\n"
            f"Improve this query — fix any errors, correct the logic, or make it "
            f"more clearly correct for the question. If it's already correct, you "
            f"may return it unchanged."
        )
        client = LLMClient(provider="ollama", model=improver)
        try:
            improved = generate_structured(
                client, improve_prompt, SQLProposal, max_retries=2,
                task_id=f"{task_id}-step{step}", system=SCHEMA_DESCRIPTION,
            )
        except Exception as e:
            # This model failed to produce a valid query (e.g. echoed the
            # schema back instead of answering). Record it as a dead-end
            # node in the tree and keep relaying from the last GOOD version —
            # this is exactly the branch-off-a-known-good-node behavior the
            # tree was designed for.
            tree.add(current.id, improver, "(failed to generate a valid query)",
                     False, f"generation error: {str(e)[:100]}")
            best = tree.best_ok_version()
            if best is None:
                break  # nothing good to branch from; give up gracefully
            current_id = best.id
            continue
        ok, rows, summary = _run_and_summarize(improved.sql_query)
        current_id = tree.add(current.id, improver, improved.sql_query, ok, summary, rows)

        # stop rule: if it runs clean AND a judge says it's good enough, stop
        if ok:
            judge_client = LLMClient(provider="ollama", model=MODELS[0])
            judge_prompt = (
                f"Question: {question}\n\nSQL: {improved.sql_query}\n\n"
                f"Execution result: {format_rows(rows)}\n\n"
                f"Is this query sound and complete for the question asked?"
            )
            try:
                verdict = generate_structured(
                    judge_client, judge_prompt, RefinementJudge, max_retries=2,
                    task_id=f"{task_id}-judge{step}",
                )
                if verdict.is_good_enough:
                    log_span(task_id=task_id, kind="relay_stop", input_summary=question[:200],
                             output_summary=f"stopped at v{current_id}: {verdict.reason[:150]}",
                             latency_s=0, cost_usd=0, tokens={}, success=True,
                             extra={"stopped_at": current_id, "steps_used": step + 1})
                    break
            except Exception:
                pass  # judge failed — keep relaying rather than crashing

    return tree