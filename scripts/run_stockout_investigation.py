"""Run a governed stockout investigation and emit deterministic structured JSON.

This is the offline smoke entrypoint used locally and in CI. It runs the agent
against the in-memory governed fixture dataset — it never connects to Snowflake
and never takes an external action. The production wiring swaps in the
``SnowflakeGateway`` / ``SnowflakeAuditSink`` implementations.
"""

from __future__ import annotations

import argparse
import json
from datetime import date

from scripts.stockout_agent import (
    AgentContext,
    InvestigationRequest,
    StockoutInvestigationAgent,
)
from scripts.stockout_agent.gateway import InMemoryAuditSink


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Governed Stockout Investigation Agent")
    parser.add_argument("--question", default="Why did stockouts increase?")
    parser.add_argument("--region", default="Melbourne")
    parser.add_argument("--category", default="pain relief")
    parser.add_argument("--window-days", type=int, default=14)
    parser.add_argument("--as-of", default="2026-02-02", help="ISO date (YYYY-MM-DD)")
    parser.add_argument("--role", default="PHARMARETAIL_SUPPLY_CHAIN_ANALYST")
    parser.add_argument("--user", default="SMOKE_USER")
    parser.add_argument("--stores", default="", help="Comma-separated allowed store ids")
    parser.add_argument("--regions", default="", help="Comma-separated allowed regions")
    parser.add_argument("--output", default=None, help="Optional path to write the JSON result")
    return parser.parse_args()


def _split(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def main() -> int:
    args = _parse_args()
    request = InvestigationRequest(
        question=args.question,
        region=args.region,
        category=args.category,
        window_days=args.window_days,
        as_of_date=date.fromisoformat(args.as_of),
    )
    context = AgentContext(
        user=args.user,
        role=args.role,
        allowed_store_ids=_split(args.stores),
        allowed_regions=_split(args.regions),
    )
    sink = InMemoryAuditSink()
    # Fixed clock keeps the smoke artifact reproducible run-to-run.
    agent = StockoutInvestigationAgent(
        audit_sink=sink, clock=lambda: f"{args.as_of}T00:00:00+00:00"
    )
    result = agent.investigate(request, context)
    document = result.to_dict()
    document["audit_records"] = [record.to_dict() for record in sink.records]
    rendered = json.dumps(document, indent=2, ensure_ascii=False)
    print(rendered)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")
    # Non-zero exit only on an unexpected refusal, so CI can gate on it.
    if result.refused:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
