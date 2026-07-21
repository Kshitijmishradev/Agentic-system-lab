"""
Aggregates logs/spans.jsonl into the numbers you actually put on your resume.
Run this after any batch of trials.
"""

from core.tracing import load_spans


def structured_output_stats():
    spans = load_spans(kind="schema_validation")
    if not spans:
        print("No schema_validation spans yet — run project 01 first.")
        return

    for label in ["baseline", "improved"]:
        label_spans = [s for s in spans if s["task_id"].startswith(label)]
        if not label_spans:
            continue
        first_attempts = [s for s in label_spans if s["extra"]["attempt"] == 1]
        final_success_task_ids = {s["task_id"] for s in label_spans if s["success"]}
        total_tasks = len({s["task_id"] for s in label_spans})

        first_pass_rate = sum(1 for s in first_attempts if s["success"]) / len(first_attempts)
        final_pass_rate = len(final_success_task_ids) / total_tasks

        print(f"[{label}] total tasks: {total_tasks}")
        print(f"[{label}] first-pass valid rate: {first_pass_rate:.1%}")
        print(f"[{label}] final valid rate (after retries allowed): {final_pass_rate:.1%}\n")

    baseline_spans = [s for s in spans if s["task_id"].startswith("baseline")]
    improved_spans = [s for s in spans if s["task_id"].startswith("improved")]
    if baseline_spans and improved_spans:
        baseline_final = len({s["task_id"] for s in baseline_spans if s["success"]}) / len(
            {s["task_id"] for s in baseline_spans}
        )
        improved_final = len({s["task_id"] for s in improved_spans if s["success"]}) / len(
            {s["task_id"] for s in improved_spans}
        )
        print(
            f"Resume line: 'Reduced malformed structured-output failure rate from "
            f"{1-baseline_final:.0%} to {1-improved_final:.0%} across "
            f"{len({s['task_id'] for s in baseline_spans})} trials via a schema-validated "
            f"retry loop.'"
        )


def react_agent_stats():
    spans = load_spans(kind="iteration")
    if not spans:
        print("No iteration spans yet — run project 03 first.")
        return

    total_tasks = len({s["task_id"] for s in spans})
    hit_cap = len({s["task_id"] for s in spans if s["extra"].get("hit_cap")})
    degraded_gracefully = len(
        {s["task_id"] for s in spans if s["extra"].get("hit_cap") and s["success"]}
    )

    print(f"Total tasks: {total_tasks}")
    print(f"Tasks that hit iteration cap: {hit_cap}")
    if hit_cap:
        print(f"Graceful degradation rate on capped tasks: {degraded_gracefully/hit_cap:.1%}")

    critique_spans = load_spans(kind="self_critique")
    if critique_spans:
        errored = [s for s in critique_spans if s["extra"].get("critique_errored")]
        real_critiques = [s for s in critique_spans if not s["extra"].get("critique_errored")]

        print(f"\nSelf-critique calls made: {len(critique_spans)}")
        if errored:
            print(f"Critique step itself failed to produce valid output: {len(errored)} time(s) (defaulted to accept)")
        if real_critiques:
            caught = sum(1 for s in real_critiques if not s["success"])
            print(f"Self-critique caught and rejected a bad answer: {caught}/{len(real_critiques)} valid critique calls")


def cost_and_latency_summary():
    spans = load_spans(kind="llm_call")
    if not spans:
        print("No llm_call spans yet.")
        return
    total_cost = sum(s["cost_usd"] for s in spans)
    latencies = sorted(s["latency_s"] for s in spans)
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    print(f"Total LLM calls: {len(spans)}")
    print(f"Total cost: ${total_cost:.4f}")
    print(f"Latency p50: {p50}s | p95: {p95}s")


if __name__ == "__main__":
    print("=== Structured Output (P1) ===")
    structured_output_stats()
    print("\n=== ReAct Agent (P3) ===")
    react_agent_stats()
    print("\n=== Cost & Latency (P11) ===")
    cost_and_latency_summary()