"""
The debate engine — the reliability core of the product.

answer_question() runs the full pipeline for one natural-language question:
  1. each model independently writes SQL (Project 1's structured output)
  2. every query is executed against the real DB (sql_tool)
  3. a critic model reviews all queries + their REAL execution results and
     picks/synthesizes the correct answer, reporting confidence + how much
     the models agreed
  4. if every model's SQL errored, one self-healing retry round runs with
     the critic's diagnosis fed back in

Returns a structured result the CLI can render (plain answer + confidence)
and the eval can score.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pydantic import BaseModel
from typing import Literal

from core.llm_client import LLMClient
from core.schemas import generate_structured
from core.tracing import log_span

from config import MODELS, CRITIC_MODEL, SCHEMA_DESCRIPTION
from sql_tool import run_sql, format_rows


class SQLProposal(BaseModel):
    sql_query: str
    reasoning: str


class CriticVerdict(BaseModel):
    final_answer: str                                   # plain-English answer for the user
    confidence: Literal["low", "medium", "high"]
    agreement_level: Literal["unanimous", "majority", "split"]
    reasoning: str


@dataclass
class Proposal:
    model: str
    sql: str = None
    reasoning: str = None
    ran_ok: bool = False
    rows: list = None
    message: str = ""
    failed_to_generate: bool = False


@dataclass
class AnswerResult:
    question: str
    final_answer: str
    confidence: str
    agreement_level: str
    critic_reasoning: str
    proposals: list = field(default_factory=list)   # for the /sql toggle
    healed: bool = False                            # did a self-heal round run?


def _gather_proposals(question: str, task_id: str, extra_hint: str = "") -> list:
    proposals = []
    for model in MODELS:
        p = Proposal(model=model)
        try:
            client = LLMClient(provider="ollama", model=model)
            prompt = f"Question: {question}"
            if extra_hint:
                prompt += f"\n\nNote: a previous attempt failed. {extra_hint}"
            proposal = generate_structured(
                client, prompt, SQLProposal, max_retries=2,
                task_id=f"{task_id}-{model}", system=SCHEMA_DESCRIPTION,
            )
            p.sql = proposal.sql_query
            p.reasoning = proposal.reasoning
            ok, rows, msg = run_sql(proposal.sql_query)
            p.ran_ok, p.rows, p.message = ok, rows, msg
        except Exception as e:
            p.failed_to_generate = True
            p.message = f"model failed to produce a query: {str(e)[:120]}"
            log_span(task_id=task_id, kind="debate_agent_failure", input_summary=question[:200],
                     output_summary=p.message, latency_s=0, cost_usd=0, tokens={},
                     success=False, extra={"model": model})
        proposals.append(p)
    return proposals


def _run_critic(question: str, proposals: list, task_id: str) -> CriticVerdict:
    lines = []
    for p in proposals:
        if p.failed_to_generate:
            lines.append(f"- {p.model}: FAILED to produce any query")
        elif not p.ran_ok:
            lines.append(f"- {p.model}: SQL ERRORED ({p.message})\n  query: {p.sql}")
        else:
            lines.append(
                f"- {p.model}: SUCCESS\n  query: {p.sql}\n  result: {format_rows(p.rows)}\n  reasoning: {p.reasoning}"
            )
    prompt = (
        f"Question: {question}\n\n"
        f"Three independent agents each wrote SQL, executed against the real database:\n\n"
        + "\n".join(lines)
        + "\n\nBased on the ACTUAL EXECUTION RESULTS (not just the SQL text), give the correct "
        "final answer to the question in plain English. A query that errored is wrong regardless "
        "of its reasoning. If the successful results disagree, judge which query logic is actually "
        "correct. Report your confidence and how much the agents agreed."
    )
    critic_client = LLMClient(provider="ollama", model=CRITIC_MODEL)
    verdict = generate_structured(
        critic_client, prompt, CriticVerdict, max_retries=2, task_id=f"{task_id}-critic"
    )
    log_span(task_id=task_id, kind="debate_critic", input_summary=question[:200],
             output_summary=verdict.final_answer[:200], latency_s=0, cost_usd=0, tokens={},
             success=True, extra={"confidence": verdict.confidence, "agreement_level": verdict.agreement_level})
    return verdict


def answer_question(question: str, task_id: str = "cli-query") -> AnswerResult:
    proposals = _gather_proposals(question, task_id)
    healed = False

    # Self-healing: if EVERY model's SQL failed to run, do one retry round
    # with a hint, rather than giving up.
    if all(p.failed_to_generate or not p.ran_ok for p in proposals):
        healed = True
        hint = "All previous queries failed. Re-read the join rules carefully, especially using team_api_id/player_api_id (not id) for joins."
        proposals = _gather_proposals(question, f"{task_id}-heal", extra_hint=hint)

    # If even after healing nothing ran, return an honest failure.
    if all(p.failed_to_generate or not p.ran_ok for p in proposals):
        return AnswerResult(
            question=question,
            final_answer="I couldn't answer this reliably — all generated queries failed to execute.",
            confidence="low", agreement_level="split",
            critic_reasoning="No agent produced a runnable query.",
            proposals=proposals, healed=healed,
        )

    verdict = _run_critic(question, proposals, task_id)
    return AnswerResult(
        question=question,
        final_answer=verdict.final_answer,
        confidence=verdict.confidence,
        agreement_level=verdict.agreement_level,
        critic_reasoning=verdict.reasoning,
        proposals=proposals, healed=healed,
    )
