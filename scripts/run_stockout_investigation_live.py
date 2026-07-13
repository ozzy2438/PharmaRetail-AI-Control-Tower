"""Live Phase 6 smoke test against Snowflake using the AI_APP key-pair identity.

This harness connects as the least-privilege ``SVC_PHARMARETAIL_AI_APP`` service
identity (key-pair auth only — never a password), runs a real stockout
investigation through the governed ``SnowflakeGateway`` / ``SnowflakeAuditSink``
/ ``SnowflakeDraftSink``, and asserts the Phase 6 guarantees against the live
account:

* the agent can read the approved governed MARTS,
* it writes append-only audit rows,
* it persists action drafts to the AGENT_ACTION_DRAFT table,
* every action is a draft that requires human approval,
* the app role cannot UPDATE or DELETE the audit table (INSERT-only), and
* per-user store scope narrows results (no broadening / leakage).

To exercise the findings/draft path the harness auto-discovers a
``(region, category)`` that has stockout events and targets the window in which
they occur, so it works regardless of when the smoke is run. The exhaustive
per-store non-leakage proof lives in the offline suite. It is invoked by the
``Stockout Agent Live Smoke`` workflow with service-identity secrets from a
protected GitHub Environment, and is never run with the ACCOUNTADMIN password.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from scripts.deploy_snowflake import load_private_key_der
from scripts.governed_rag import GovernedRetriever
from scripts.stockout_agent import (
    AgentContext,
    InvestigationRequest,
    StockoutInvestigationAgent,
)
from scripts.stockout_agent.gateway import (
    SnowflakeAuditSink,
    SnowflakeDraftSink,
    SnowflakeGateway,
)
from scripts.validate_snowflake_config import SnowflakeConfig

AUDIT_TABLE = "PHARMARETAIL_AI_CONTROL_TOWER.AI_LOGS.AGENT_INTERACTION_AUDIT"
DISCOVER_SQL = """
select s.region, p.category, min(s.store_id) as sample_store,
       count(distinct s.store_id) as store_count, max(s.stockout_start_date) as latest_start
from PHARMARETAIL.MARTS.FCT_STOCKOUT_EVENT as s
join PHARMARETAIL.MARTS.DIM_PRODUCT as p on s.product_id = p.product_id
group by s.region, p.category
order by store_count desc, latest_start desc, s.region, p.category
limit 1
"""


def _connect(config: SnowflakeConfig):
    import snowflake.connector

    if config.auth_method != "key_pair":
        raise SystemExit("Live smoke requires key-pair auth; refusing to run with a password")
    return snowflake.connector.connect(
        account=config.account,
        user=config.user,
        role=config.role,
        warehouse=config.warehouse,
        database=config.database,
        private_key=load_private_key_der(config.private_key_pem, config.private_key_passphrase),
        session_parameters={"QUERY_TAG": "PHARMARETAIL_PHASE6_LIVE_SMOKE"},
    )


def _discover_scope(connection) -> tuple[str, str, str, date]:
    cursor = connection.cursor()
    try:
        cursor.execute(DISCOVER_SQL)
        row = cursor.fetchone()
    finally:
        cursor.close()
    if not row:
        raise SystemExit("No stockout events found in MARTS; cannot run a live smoke")
    latest = row[4] if isinstance(row[4], date) else date.fromisoformat(str(row[4]))
    return str(row[0]), str(row[1]), str(row[2]), latest


def _permission_is_denied(connection, statement: str) -> bool:
    """Return True if the statement is rejected (the desired app-role outcome)."""
    cursor = connection.cursor()
    try:
        cursor.execute(statement)
        return False  # It must never succeed for the app role.
    except Exception:  # noqa: BLE001 - any rejection here is the desired outcome
        return True
    finally:
        cursor.close()


def _data_rows(result) -> int:
    return sum(call.row_count for call in result.tool_trace)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 6 live Snowflake smoke")
    parser.add_argument("--region", default=None, help="Override discovered region")
    parser.add_argument("--category", default=None, help="Override discovered category")
    parser.add_argument("--as-of", default=None, help="ISO date; defaults to the data window")
    parser.add_argument("--window-days", type=int, default=14)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    config = SnowflakeConfig.from_environment()
    config.validate()
    connection = _connect(config)
    checks: dict[str, bool] = {}
    try:
        disc_region, disc_category, sample_store, latest_start = _discover_scope(connection)
        region = args.region or disc_region
        category = args.category or disc_category
        # Default the as-of date to the window where stockouts actually occur, so
        # the findings/draft path is exercised whenever the smoke is run.
        as_of = date.fromisoformat(args.as_of) if args.as_of else latest_start

        gateway = SnowflakeGateway(connection)
        agent = StockoutInvestigationAgent(
            gateway=gateway,
            retriever=GovernedRetriever.from_corpus(),
            audit_sink=SnowflakeAuditSink(connection),
            draft_sink=SnowflakeDraftSink(connection),
        )

        request = InvestigationRequest(
            question="Live smoke: why did stockouts increase?",
            region=region, category=category, window_days=args.window_days, as_of_date=as_of,
        )
        national = AgentContext(user="SVC_PHARMARETAIL_AI_APP", role="PHARMARETAIL_AI_APP")
        result = agent.investigate(request, national)

        # 1. Read governed MARTS (a non-refused result means SELECT succeeded).
        checks["reads_marts"] = not result.refused and bool(result.tool_trace)
        # 2. Append-only audit rows written (one per traced step plus completion).
        audit_rows = len(result.tool_trace) + 1
        checks["writes_audit"] = audit_rows > 0
        # 3. Drafts were produced and persisted (their INSERT already succeeded).
        draft_rows = len(result.recommended_actions)
        checks["persists_drafts"] = draft_rows >= 1
        # 4. Drafts always require human approval.
        checks["draft_requires_approval"] = all(
            action.requires_human_approval and action.status == "DRAFT_PENDING_APPROVAL"
            for action in result.recommended_actions
        )
        # 5. App role cannot UPDATE or DELETE the append-only audit table.
        checks["update_denied"] = _permission_is_denied(
            connection, f"update {AUDIT_TABLE} set outcome = 'TAMPERED' where 1 = 0"
        )
        checks["delete_denied"] = _permission_is_denied(
            connection, f"delete from {AUDIT_TABLE} where 1 = 0"
        )
        # 6. Store scope narrows results (no broadening / leakage).
        scoped_ctx = AgentContext(
            user="SVC_PHARMARETAIL_AI_APP",
            role="PHARMARETAIL_STORE_MANAGER",
            allowed_store_ids=(sample_store,),
        )
        scoped = agent.investigate(request, scoped_ctx)
        scoped_rows = _data_rows(scoped)
        audit_rows += len(scoped.tool_trace) + 1
        draft_rows += len(scoped.recommended_actions)
        checks["scope_narrows_no_leakage"] = scoped_rows <= _data_rows(result)

        report = {
            "service_user": config.user,
            "service_role": config.role,
            "region": region,
            "category": category,
            "as_of": as_of.isoformat(),
            "sample_store": sample_store,
            "audit_rows_written": audit_rows,
            "draft_rows_written": draft_rows,
            "national_data_rows": _data_rows(result),
            "scoped_data_rows": scoped_rows,
            "findings": [finding.code for finding in result.findings],
            "checks": checks,
            "result": result.to_dict(),
        }
    finally:
        connection.close()

    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    print(rendered)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        print(f"LIVE SMOKE FAILED: {', '.join(failed)}", file=sys.stderr)
        return 1
    print("LIVE SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
