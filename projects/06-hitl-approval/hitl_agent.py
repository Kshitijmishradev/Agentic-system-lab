"""
Project 6 — the pause/resume mechanism.

process_request() gets a model decision, checks it against our OWN trigger
logic (not the model's), and if triggered, pauses for a human response.

simulate_human: pass None for a REAL interactive pause (uses input()).
Pass a string like "approve" / "reject" to run automated batch evals
without blocking on a real terminal prompt — this is what run_project6.py
uses to test trigger accuracy across many requests without you sitting
there approving each one by hand.

Every outcome — proposed decision, whether it was paused, what the human
(real or simulated) decided, final outcome — gets logged as one audit
entry via tracing.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.llm_client import LLMClient
from core.schemas import generate_structured
from core.tracing import log_span

from refund_schema import RefundDecision, requires_human_review

SYSTEM_PROMPT = """You triage customer refund requests. Propose an action:
auto_approve, deny, or escalate. Extract the refund dollar amount from the
request. Rate your own confidence honestly — say "low" if the request is
ambiguous, lacks evidence, or is unusually large."""


def process_request(request_text: str, client: LLMClient, task_id: str, simulate_human=None):
    prompt = f"Refund request: \"{request_text}\""
    decision = generate_structured(
        client, prompt, RefundDecision, max_retries=2, task_id=task_id, system=SYSTEM_PROMPT
    )

    triggered, trigger_reason = requires_human_review(decision)

    if not triggered:
        log_span(
            task_id=task_id,
            kind="hitl_trigger",
            input_summary=request_text[:200],
            output_summary=f"auto-{decision.proposed_action}",
            latency_s=0, cost_usd=0, tokens={},
            success=True,
            extra={
                "triggered": False,
                "trigger_reason": trigger_reason,
                "proposed_action": decision.proposed_action,
                "refund_amount": decision.refund_amount,
                "confidence": decision.confidence,
                "final_action": decision.proposed_action,
                "human_response": None,
            },
        )
        return decision.proposed_action, False

    # --- PAUSED: human review required ---
    print(f"\n--- HUMAN REVIEW NEEDED ({trigger_reason}) ---")
    print(f"Request: {request_text}")
    print(f"Model proposes: {decision.proposed_action} | amount: ${decision.refund_amount:.2f} | confidence: {decision.confidence}")
    print(f"Model reasoning: {decision.reasoning}")

    if simulate_human is not None:
        human_response = simulate_human
    else:
        human_response = input("Approve / Reject / Edit — type your decision: ").strip().lower()

    final_action = decision.proposed_action if human_response == "approve" else human_response

    log_span(
        task_id=task_id,
        kind="hitl_trigger",
        input_summary=request_text[:200],
        output_summary=f"paused -> human said: {human_response}",
        latency_s=0, cost_usd=0, tokens={},
        success=True,
        extra={
            "triggered": True,
            "trigger_reason": trigger_reason,
            "proposed_action": decision.proposed_action,
            "refund_amount": decision.refund_amount,
            "confidence": decision.confidence,
            "final_action": final_action,
            "human_response": human_response,
        },
    )
    print(f"--- RESUMED: final action = {final_action} ---\n")
    return final_action, True
