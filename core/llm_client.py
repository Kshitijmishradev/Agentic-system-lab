"""
Thin wrapper around the Anthropic API: retries transient failures,
tracks tokens/cost, and hands every call to tracing.py.

Set ANTHROPIC_API_KEY in your environment before running.
"""

import os
import time
import requests
from dataclasses import dataclass
from typing import Optional

from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from core.tracing import log_span

# Rough per-model pricing ($ / 1M tokens) — update if you change models.
# Ollama models aren't priced (local/free) so they aren't listed here;
# cost defaults to $0 for anything not in this dict.
PRICING = {
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
}

DEFAULT_MODEL = "claude-sonnet-4-6"
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_s: float
    model: str


class LLMClient:
    def __init__(self, model: str = DEFAULT_MODEL, max_tokens: int = 1024, provider: str = "anthropic"):
        """
        provider: "anthropic" (default) or "ollama".
        For ollama, pass a model name you've pulled locally, e.g. model="llama3.1".
        """
        self.provider = provider
        self.model = model
        self.max_tokens = max_tokens
        if provider == "anthropic":
            self.client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
    )
    def _call_anthropic(self, messages: list, system: Optional[str] = None):
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        return self.client.messages.create(**kwargs)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
    )
    def _call_ollama(self, messages: list, system: Optional[str] = None):
        # Ollama's /api/chat mirrors the messages-array shape Anthropic uses,
        # so system just becomes the first message with role "system".
        full_messages = ([{"role": "system", "content": system}] if system else []) + messages
        resp = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            json={"model": self.model, "messages": full_messages, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()

    def complete(self, prompt: str, system: Optional[str] = None, task_id: str = "unlabeled") -> LLMResponse:
        start = time.time()
        messages = [{"role": "user", "content": prompt}]

        if self.provider == "anthropic":
            resp = self._call_anthropic(messages, system=system)
            text = "".join(block.text for block in resp.content if block.type == "text")
            in_tok = resp.usage.input_tokens
            out_tok = resp.usage.output_tokens
        elif self.provider == "ollama":
            resp = self._call_ollama(messages, system=system)
            text = resp["message"]["content"]
            # Ollama reports token counts under different keys; fall back to 0 if absent.
            in_tok = resp.get("prompt_eval_count", 0)
            out_tok = resp.get("eval_count", 0)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        latency = time.time() - start
        price = PRICING.get(self.model, {"input": 0, "output": 0})
        cost = (in_tok / 1_000_000) * price["input"] + (out_tok / 1_000_000) * price["output"]

        result = LLMResponse(
            text=text,
            input_tokens=in_tok,
            output_tokens=out_tok,
            cost_usd=round(cost, 6),
            latency_s=round(latency, 3),
            model=self.model,
        )

        log_span(
            task_id=task_id,
            kind="llm_call",
            input_summary=prompt[:200],
            output_summary=text[:200],
            latency_s=result.latency_s,
            cost_usd=result.cost_usd,
            tokens={"input": in_tok, "output": out_tok},
            success=True,
        )
        return result