"""
Project 3 — the ReAct loop.

think -> act -> observe -> reflect, repeated, with a hard iteration cap.
Every iteration's decision is forced through generate_structured() (from
Project 1) so parsing the model's chosen action is never fragile regex.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # repo root on path

from core.llm_client import LLMClient
from core.schemas import generate_structured
from core.tracing import log_span

from agent_step_schema import AgentStep, CritiqueResult
from tools import TOOLS, TOOL_DESCRIPTIONS

MAX_ITERATIONS = 6

SYSTEM_PROMPT = f"""You are a research agent. You answer questions by taking
one step at a time. You have these tools available:

{TOOL_DESCRIPTIONS}

At each step, think about what you need next, then either call a tool or
finish. Only choose action "finish" when you have everything needed to give
a complete, correct final answer — put that final answer in action_input.
"""

CRITIQUE_PROMPT_TEMPLATE = """Task: {task}

Evidence gathered so far:
{transcript}

Proposed final answer: {proposed_answer}

Critically check this answer against the evidence above. Does the math check
out? Does it actually answer what was asked? Is anything missing or
misread? Be skeptical — don't just rubber-stamp it.
"""


def _critique(task: str, history: list, proposed_answer: str, client: LLMClient, task_id: str, iteration: int):
    transcript = "\n".join(history) if history else "(no tool calls made)"
    prompt = CRITIQUE_PROMPT_TEMPLATE.format(
        task=task, transcript=transcript, proposed_answer=proposed_answer
    )
    try:
        result = generate_structured(
            client, prompt, CritiqueResult, max_retries=2, task_id=f"{task_id}-critique{iteration}"
        )
        log_span(
            task_id=task_id,
            kind="self_critique",
            input_summary=proposed_answer[:200],
            output_summary=result.reason[:200],
            latency_s=0,
            cost_usd=0,
            tokens={},
            success=result.is_valid,
            extra={"iteration": iteration, "critique_errored": False},
        )
        return result
    except Exception as e:
        # Critique itself failed to produce valid output (e.g. the model
        # answered in prose instead of JSON). Don't crash the whole run —
        # default to accepting the proposed answer, since we have no
        # trustworthy verdict either way, and log this as its own honest
        # category rather than conflating it with a real rejection.
        log_span(
            task_id=task_id,
            kind="self_critique",
            input_summary=proposed_answer[:200],
            output_summary=f"critique step errored: {str(e)[:150]}",
            latency_s=0,
            cost_usd=0,
            tokens={},
            success=True,  # defaulting to accept
            extra={"iteration": iteration, "critique_errored": True},
        )
        return CritiqueResult(is_valid=True, reason="critique step failed to produce valid output; defaulted to accept")


def run_agent(task: str, client: LLMClient, task_id: str):
    history = []  # list of "Thought / Action / Observation" text blocks
    hit_cap = True  # flips to False as soon as the model finishes AND passes critique
    critique_caught_something = False
    decision_step_failed = False

    for iteration in range(1, MAX_ITERATIONS + 1):
        transcript = "\n".join(history) if history else "(nothing yet)"
        prompt = f"Task: {task}\n\nHistory so far:\n{transcript}\n\nWhat's your next step?"

        try:
            step = generate_structured(
                client, prompt, AgentStep, max_retries=2, task_id=f"{task_id}-step{iteration}",
                system=SYSTEM_PROMPT,
            )
        except Exception as e:
            # The model failed to produce a valid decision at all (e.g. wrote
            # prose instead of JSON, even after retries). Don't crash — treat
            # this exactly like running out of iterations: drop into the same
            # graceful-degradation fallback below.
            decision_step_failed = True
            history.append(f"(step {iteration} failed to produce a valid decision: {str(e)[:150]})")
            break

        if step.action == "finish":
            critique = _critique(task, history, step.action_input, client, task_id, iteration)

            if critique.is_valid:
                hit_cap = False
                log_span(
                    task_id=task_id,
                    kind="iteration",
                    input_summary=task[:200],
                    output_summary=step.action_input[:200],
                    latency_s=0,
                    cost_usd=0,
                    tokens={},
                    success=True,
                    extra={
                        "hit_cap": False,
                        "iterations_used": iteration,
                        "critique_caught_something": critique_caught_something,
                    },
                )
                return step.action_input, iteration, False

            # Critique rejected the answer — don't finish, feed the critique
            # back in as a new observation and force another iteration.
            critique_caught_something = True
            history.append(
                f"Thought: {step.thought}\nAction: finish({step.action_input})\n"
                f"Self-critique REJECTED this answer: {critique.reason}"
            )
            continue

        # Run the actual tool the model asked for.
        tool_fn = TOOLS[step.action]
        observation = tool_fn(step.action_input)
        history.append(
            f"Thought: {step.thought}\nAction: {step.action}({step.action_input})\n"
            f"Observation: {observation}"
        )

    # Hit the iteration cap without finishing — graceful degradation:
    # force one last "give your best answer now" call instead of crashing.
    transcript = "\n".join(history)
    fallback_prompt = (
        f"Task: {task}\n\nHistory so far:\n{transcript}\n\n"
        f"You're out of steps. Give your best final answer now, even if incomplete."
    )
    fallback = client.complete(fallback_prompt, task_id=f"{task_id}-fallback")

    log_span(
        task_id=task_id,
        kind="iteration",
        input_summary=task[:200],
        output_summary=fallback.text[:200],
        latency_s=0,
        cost_usd=0,
        tokens={},
        success=True,  # returned SOMETHING usable rather than crashing
        extra={
            "hit_cap": True,
            "iterations_used": iteration if decision_step_failed else MAX_ITERATIONS,
            "critique_caught_something": critique_caught_something,
            "decision_step_failed": decision_step_failed,
        },
    )
    return fallback.text, MAX_ITERATIONS, True