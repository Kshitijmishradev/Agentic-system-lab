"""
Project 11: Observability backbone.
Every LLM call, tool call, and validation attempt across every project
gets logged here as one JSON line. aggregate.py reads this file to produce
your dashboard numbers and resume stats.
"""

import json
import time
from pathlib import Path
from typing import Optional

LOG_PATH = Path(__file__).parent.parent / "logs" / "spans.jsonl"
LOG_PATH.parent.mkdir(exist_ok=True)


def log_span(
    task_id: str,
    kind: str,
    input_summary: str,
    output_summary: str,
    latency_s: float,
    cost_usd: float,
    tokens: dict,
    success: bool,
    extra: Optional[dict] = None,
):
    record = {
        "ts": time.time(),
        "task_id": task_id,
        "kind": kind,  # "llm_call" | "schema_validation" | "tool_call" | "iteration" | "hitl_trigger"
        "input_summary": input_summary,
        "output_summary": output_summary,
        "latency_s": latency_s,
        "cost_usd": cost_usd,
        "tokens": tokens,
        "success": success,
        "extra": extra or {},
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


def load_spans(kind: Optional[str] = None) -> list[dict]:
    if not LOG_PATH.exists():
        return []
    spans = [json.loads(line) for line in open(LOG_PATH) if line.strip()]
    if kind:
        spans = [s for s in spans if s["kind"] == kind]
    return spans
