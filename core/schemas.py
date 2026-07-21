"""
Project 1: Structured Output.
Forces LLM output into a Pydantic schema. On validation failure, re-prompts
with the exact error and retries. Every attempt (pass or fail) is logged —
that log is where your resume number comes from.
"""

import json
import re
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from core.llm_client import LLMClient
from core.tracing import log_span

T = TypeVar("T", bound=BaseModel)


def _find_json_objects(text: str) -> list[str]:
    """Scan for every complete, balanced {...} block in the text."""
    objects = []
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    objects.append(text[start:i + 1])
    return objects


def _extract_json(text: str) -> str:
    """
    Strip markdown fences / surrounding prose, and handle models that echo
    the schema back before their actual answer (common with smaller local
    models) — try the LAST complete JSON object found, since the real
    answer usually comes after any echoed schema, not before.
    """
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidates = [fenced.group(1)] if fenced else []
    candidates += _find_json_objects(text)

    for candidate in reversed(candidates):
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            continue

    return text  # nothing parsed — return raw text, let Pydantic's error drive the retry


def generate_structured(
    client: LLMClient,
    prompt: str,
    schema: Type[T],
    max_retries: int = 3,
    task_id: str = "structured-output",
    system: str = None,
) -> T:
    """
    Returns a validated instance of `schema`, or raises ValidationError
    after max_retries exhausted. Logs every attempt.
    """
    schema_hint = json.dumps(schema.model_json_schema(), indent=2)
    full_prompt = (
        f"{prompt}\n\nRespond ONLY with JSON matching this schema, no prose, "
        f"no markdown fences:\n{schema_hint}"
    )

    last_error = None
    for attempt in range(1, max_retries + 1):
        resp = client.complete(full_prompt, system=system, task_id=task_id)
        raw = _extract_json(resp.text)

        try:
            parsed = schema.model_validate_json(raw)
            log_span(
                task_id=task_id,
                kind="schema_validation",
                input_summary=f"attempt {attempt}",
                output_summary="valid",
                latency_s=0,
                cost_usd=0,
                tokens={},
                success=True,
                extra={"attempt": attempt},
            )
            return parsed
        except ValidationError as e:
            last_error = e
            log_span(
                task_id=task_id,
                kind="schema_validation",
                input_summary=f"attempt {attempt}",
                output_summary=str(e)[:300],
                latency_s=0,
                cost_usd=0,
                tokens={},
                success=False,
                extra={"attempt": attempt},
            )
            full_prompt = (
                f"{prompt}\n\nYour last response failed validation with this error:\n"
                f"{e}\n\nReturn ONLY corrected JSON matching this schema:\n{schema_hint}"
            )
    if last_error is None:
        raise RuntimeError("Structured generation failed without a validation error")
    raise last_error
