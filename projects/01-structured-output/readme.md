# Project 1 — Structured Output Agent

Forces LLM output into a validated Pydantic schema. On a validation failure,
the exact Pydantic error is fed back to the model as a correction prompt and
it retries — up to `max_retries` times. Every attempt (pass or fail) is
logged, so the improvement from the retry loop is measured, not assumed.

**Task used for the demo:** customer support ticket triage — given a raw,
often messy ticket, extract `category`, `priority`, `sentiment`,
`requires_human`, and a `summary` as strict structured data.

## Why this matters

LLMs are usually close to right when asked for JSON, but "usually" breaks
production systems — a missing field, a value that doesn't match the
allowed set, or a stray markdown fence is enough to crash a naive
`json.loads()` call. This project measures how much a schema-validated
retry loop closes that gap versus a single unchecked attempt.

## Setup

```bash
pip install -r ../../requirements.txt

# Anthropic:
export ANTHROPIC_API_KEY=your_key_here

# OR run locally for free with Ollama:
# ollama pull llama3.1
# ollama serve
```

To switch providers, edit the `LLMClient()` call in `run_project1.py`:

```python
client = LLMClient()                                   # Anthropic
client = LLMClient(provider="ollama", model="llama3.1") # Ollama, local, free
```

## Run it

```bash
python run_project1.py       # runs baseline (max_retries=1) vs improved (max_retries=3)
cd ../..
python -m core.eval          # aggregates logs/spans.jsonl into the stats below
```

## Test set

30 hand-written support tickets in `test_tickets.py` — 10 clean/unambiguous,
20 deliberately messy (sarcasm, ambiguous category, run-on rants, mixed
sentiment). The messy tickets are what actually trigger validation failures;
a retry loop tested only on easy inputs wouldn't prove anything.

## Results

Run locally against Ollama (`llama3.1`), zero API cost:

| | Baseline (max_retries=1) | Improved (max_retries=3) |
|---|---|---|
| First-pass valid rate | 46.7% | 53.3% |
| Final valid rate | 46.7% | **90.0%** |

**Reduced malformed structured-output failure rate from 53% to 10% across
30 trials via a schema-validated retry loop.**

Notes:
- Baseline and improved first-pass rates differ slightly (46.7% vs 53.3%)
  due to normal run-to-run LLM variance — the real signal is the final
  valid rate after retries are allowed (46.7% → 90.0%), since baseline
  never gets a second attempt at all.
- Local open-weight models are weaker at strict schema-following than
  hosted frontier models, which is expected — it makes the retry loop's
  impact more visible, not less valid.

## Files

- `ticket_schema.py` — the Pydantic contract (`TicketTriage`)
- `test_tickets.py` — the 30-ticket test set
- `run_project1.py` — runs baseline vs improved passes, logs every attempt
- Results are read from `../../logs/spans.jsonl` via `core/eval.py`