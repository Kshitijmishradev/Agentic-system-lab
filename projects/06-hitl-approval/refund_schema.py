"""
Project 6 — schema for a refund triage decision.

The model proposes a decision. Our OWN code (not the model) decides whether
that decision is risky enough to require human sign-off — that trigger
logic living outside the LLM is the whole point: you don't want the thing
being reviewed also deciding whether it needs review.
"""

from pydantic import BaseModel
from typing import Literal

REFUND_AMOUNT_THRESHOLD = 300.0  # above this, always escalate regardless of model confidence


class RefundDecision(BaseModel):
    proposed_action: Literal["auto_approve", "deny", "escalate"]
    refund_amount: float
    confidence: Literal["low", "medium", "high"]
    reasoning: str


def requires_human_review(decision: RefundDecision) -> tuple[bool, str]:
    """
    Our own deterministic trigger logic — NOT delegated to the model.
    Returns (should_pause, reason).
    """
    if decision.proposed_action == "escalate":
        return True, "model itself flagged this for escalation"
    if decision.refund_amount > REFUND_AMOUNT_THRESHOLD:
        return True, f"refund amount ${decision.refund_amount:.2f} exceeds ${REFUND_AMOUNT_THRESHOLD} threshold"
    if decision.confidence == "low":
        return True, "model confidence is low"
    return False, "within auto-approval bounds"
