"""
Project 11 — Observability dashboard.

Reads logs/spans.jsonl FRESH every time you run this (not hand-edited,
not baked-in data) and writes dashboard.html. Re-run this after any new
batch of project runs to refresh the numbers:

    python core/generate_dashboard.py

Then open logs/dashboard.html in a browser.
"""

import json
from collections import defaultdict
from pathlib import Path

from core.tracing import load_spans

OUTPUT_PATH = Path(__file__).parent.parent / "logs" / "dashboard.html"


def build_dashboard():
    all_spans = load_spans()
    if not all_spans:
        print("No spans logged yet — run a project first.")
        return

    llm_calls = [s for s in all_spans if s["kind"] == "llm_call"]
    iterations = [s for s in all_spans if s["kind"] == "iteration"]
    critiques = [s for s in all_spans if s["kind"] == "self_critique"]
    validations = [s for s in all_spans if s["kind"] == "schema_validation"]

    total_cost = sum(s["cost_usd"] for s in llm_calls)
    total_calls = len(llm_calls)
    latencies = sorted(s["latency_s"] for s in llm_calls) if llm_calls else [0]
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0]

    total_tasks = len({s["task_id"] for s in iterations}) if iterations else 0
    hit_cap = len({s["task_id"] for s in iterations if s["extra"].get("hit_cap")})
    cap_rate = (hit_cap / total_tasks * 100) if total_tasks else 0

    critique_valid = [c for c in critiques if not c["extra"].get("critique_errored")]
    critique_caught = sum(1 for c in critique_valid if not c["success"])

    # cost/latency over time, bucketed by call order, for a simple sparkline-style table
    timeline_rows = ""
    for s in llm_calls[-20:]:  # last 20 calls
        timeline_rows += (
            f"<tr><td>{s['task_id']}</td><td>{s['latency_s']}s</td>"
            f"<td>${s['cost_usd']:.5f}</td><td>{s['tokens'].get('input',0)}/{s['tokens'].get('output',0)}</td></tr>\n"
        )

    alerts = []
    if cap_rate > 50:
        alerts.append(f"⚠ {cap_rate:.0f}% of tasks are hitting the iteration cap — loop may be under-provisioned or task too hard for the model.")
    fail_rate_validations = (
        sum(1 for v in validations if not v["success"]) / len(validations) if validations else 0
    )
    if fail_rate_validations > 0.3:
        alerts.append(f"⚠ Schema validation failure rate is {fail_rate_validations:.0%} — retry budget may need raising.")
    if not alerts:
        alerts.append("✓ No thresholds breached in current data.")

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Agentic Systems Lab — Observability Dashboard</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #1a1a1a; }}
  h1 {{ font-size: 22px; }}
  h2 {{ font-size: 16px; margin-top: 32px; border-bottom: 1px solid #ddd; padding-bottom: 6px; }}
  .stat-row {{ display: flex; gap: 16px; flex-wrap: wrap; margin: 12px 0; }}
  .stat {{ background: #f6f6f6; border-radius: 8px; padding: 12px 16px; min-width: 140px; }}
  .stat .label {{ font-size: 12px; color: #666; }}
  .stat .value {{ font-size: 20px; font-weight: 600; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  td, th {{ border-bottom: 1px solid #eee; padding: 6px 8px; text-align: left; }}
  .alert {{ background: #fff8e6; border-left: 3px solid #e6a700; padding: 8px 12px; margin: 6px 0; font-size: 14px; }}
  .footer {{ margin-top: 40px; font-size: 12px; color: #888; }}
</style>
</head>
<body>
  <h1>Agentic Systems Lab — Observability Dashboard</h1>
  <p style="color:#666; font-size:13px;">Regenerated from logs/spans.jsonl — re-run generate_dashboard.py after new project runs to refresh.</p>

  <h2>Alerts</h2>
  {''.join(f'<div class="alert">{a}</div>' for a in alerts)}

  <h2>Cost & Latency (across all projects)</h2>
  <div class="stat-row">
    <div class="stat"><div class="label">Total LLM calls</div><div class="value">{total_calls}</div></div>
    <div class="stat"><div class="label">Total cost</div><div class="value">${total_cost:.4f}</div></div>
    <div class="stat"><div class="label">Latency p50</div><div class="value">{p50}s</div></div>
    <div class="stat"><div class="label">Latency p95</div><div class="value">{p95}s</div></div>
  </div>

  <h2>ReAct Loop (Project 3)</h2>
  <div class="stat-row">
    <div class="stat"><div class="label">Total tasks</div><div class="value">{total_tasks}</div></div>
    <div class="stat"><div class="label">Hit iteration cap</div><div class="value">{hit_cap} ({cap_rate:.0f}%)</div></div>
    <div class="stat"><div class="label">Self-critique catches</div><div class="value">{critique_caught}/{len(critique_valid)}</div></div>
  </div>

  <h2>Structured Output (Project 1)</h2>
  <div class="stat-row">
    <div class="stat"><div class="label">Validation attempts logged</div><div class="value">{len(validations)}</div></div>
    <div class="stat"><div class="label">Failure rate</div><div class="value">{fail_rate_validations:.0%}</div></div>
  </div>

  <h2>Recent LLM calls (last 20)</h2>
  <table>
    <tr><th>Task ID</th><th>Latency</th><th>Cost</th><th>Tokens (in/out)</th></tr>
    {timeline_rows}
  </table>

  <div class="footer">Generated from {len(all_spans)} total logged spans.</div>
</body>
</html>"""

    OUTPUT_PATH.write_text(html)
    print(f"Dashboard written to {OUTPUT_PATH}")


if __name__ == "__main__":
    build_dashboard()