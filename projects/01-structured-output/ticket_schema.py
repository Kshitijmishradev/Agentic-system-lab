"""
Project 1: Structured Output — schema definition.

This is the "contract": every triaged ticket must match this shape exactly,
or Pydantic rejects it and generate_structured() retries with the error.
"""

from pydantic import BaseModel
from typing import Literal


class TicketTriage(BaseModel):
    category: Literal["billing", "bug", "feature_request", "account", "other"]
    priority: Literal["low", "medium", "high", "urgent"]
    sentiment: Literal["positive", "neutral", "negative", "angry"]
    requires_human: bool
    summary: str
