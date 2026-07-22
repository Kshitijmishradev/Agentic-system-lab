"""
Project 6 (extension) — iterative HITL refinement.

Different flavor of human-in-the-loop from hitl_agent.py: instead of one
pause-point with approve/reject, this loops indefinitely — the agent
proposes a revision, you give free-text feedback, it revises again, repeat
until you type "approve". Every round is logged: original, proposed,
your feedback, and what happened next.

Genuinely useful as-is: run it on your real resume bullets.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pydantic import BaseModel

from core.llm_client import LLMClient
from core.schemas import generate_structured
from core.tracing import log_span

SYSTEM_PROMPT = """You improve resume bullet points. Make them concise,
results-oriented, and quantified where reasonable, without inventing facts
that weren't given to you. Follow the human's specific feedback exactly
when they give it."""


class BulletRevision(BaseModel):
    proposed_text: str
    reasoning: str


def refine_bullet(original_bullet: str, client: LLMClient, task_id: str, max_rounds: int = 10):
    history = []
    instruction = "Improve this bullet to be more concise and results-oriented."
    round_num = 0

    while round_num < max_rounds:
        round_num += 1
        past = "\n".join(history) if history else "(first round)"
        prompt = (
            f"Original bullet: \"{original_bullet}\"\n\n"
            f"Revision history so far:\n{past}\n\n"
            f"Current instruction: {instruction}\n\n"
            f"Propose a revised version of the bullet."
        )
        revision = generate_structured(
            client, prompt, BulletRevision, max_retries=2,
            task_id=f"{task_id}-round{round_num}", system=SYSTEM_PROMPT,
        )

        print(f"\n--- Round {round_num} ---")
        print(f"Proposed: {revision.proposed_text}")
        print(f"Reasoning: {revision.reasoning}")
        feedback = input("Feedback to revise further, or type 'approve' to accept: ").strip()

        log_span(
            task_id=task_id,
            kind="hitl_resume_edit",
            input_summary=original_bullet[:200],
            output_summary=revision.proposed_text[:200],
            latency_s=0, cost_usd=0, tokens={},
            success=True,
            extra={"round": round_num, "human_feedback": feedback, "approved": feedback.lower() == "approve"},
        )

        if feedback.lower() in ("approve", "done", "accept"):
            print(f"\nFinal approved bullet: {revision.proposed_text}")
            return revision.proposed_text, round_num

        history.append(f"Round {round_num}: proposed \"{revision.proposed_text}\" — human said: \"{feedback}\"")
        instruction = feedback

    print("\nHit max rounds without approval — returning last proposed version.")
    return revision.proposed_text, round_num


if __name__ == "__main__":
    client = LLMClient()  # or LLMClient(provider="ollama", model="llama3.1")
    bullet = input("Paste a resume bullet to refine: ").strip()
    refine_bullet(bullet, client, task_id="resume-refine-1")
