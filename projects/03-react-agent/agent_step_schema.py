"""
Project 3 — the schema for a single agent decision.
Every iteration of the loop asks the model to fill this out, using the same
generate_structured() retry machinery from Project 1.
"""

from pydantic import BaseModel
from typing import Literal


class AgentStep(BaseModel):
    thought: str  # the model's reasoning about what to do next
    action: Literal["calculator", "country_lookup", "city_population_lookup", "finish"]
    action_input: str  # tool input, OR the final answer text when action == "finish"


class CritiqueResult(BaseModel):
    is_valid: bool          # does the proposed answer actually hold up against the evidence?
    reason: str             # why — what's missing or wrong, or why it checks out

