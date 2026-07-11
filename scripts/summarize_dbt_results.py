"""Render a dbt run_results.json artifact as a markdown summary.

Used by the dbt GitHub Actions workflows to post build/test results as a PR
comment and a job step summary. dbt build's own exit code already fails the
workflow on any model/test failure; this script only renders, it does not
re-decide pass/fail.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def summarize(run_results: dict) -> str:
    results = run_results.get("results", [])
    metadata = run_results.get("metadata", {})

    status_counts: dict[str, int] = {}
    rows = []
    for result in results:
        unique_id = result.get("unique_id", "unknown")
        parts = unique_id.split(".")
        resource_type = parts[0] if len(parts) > 1 else "unknown"
        # Test unique_ids are "test.<package>.<name>.<hash>"; the trailing
        # hash isn't useful in a human-facing summary, so drop it there.
        if resource_type == "test" and len(parts) == 4:
            name = parts[2]
        else:
            name = parts[-1]
        status = str(result.get("status", "unknown"))
        status_counts[status] = status_counts.get(status, 0) + 1
        execution_time = result.get("execution_time", 0) or 0
        rows.append((name, resource_type, status, execution_time))

    summary_line = (
        ", ".join(f"{count} {status}" for status, count in sorted(status_counts.items()))
        or "no results"
    )

    lines = [
        "## dbt run summary",
        "",
        f"dbt version: {metadata.get('dbt_version', 'unknown')}",
        f"Generated: {metadata.get('generated_at', 'unknown')}",
        f"Summary: {summary_line}",
        "",
        "| Node | Type | Status | Execution time (s) |",
        "|---|---|---|---:|",
    ]
    for name, resource_type, status, execution_time in rows:
        lines.append(f"| {name} | {resource_type} | {status} | {execution_time:.2f} |")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-results", type=Path, default=Path("dbt/pharma_retail/target/run_results.json")
    )
    parser.add_argument("--output", type=Path, default=Path("dbt_run_summary.md"))
    args = parser.parse_args()

    if not args.run_results.exists():
        message = f"No run_results.json found at {args.run_results}; dbt may not have run.\n"
        args.output.write_text(message, encoding="utf-8")
        print(message)
        return 1

    run_results = json.loads(args.run_results.read_text(encoding="utf-8"))
    summary = summarize(run_results)
    args.output.write_text(summary, encoding="utf-8")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
