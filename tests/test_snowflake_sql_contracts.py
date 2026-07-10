from __future__ import annotations

from pathlib import Path

SQL_DIRECTORY = Path("infra/snowflake")


def test_foundation_sql_never_references_abs_data() -> None:
    for path in SQL_DIRECTORY.glob("*.sql"):
        executable_sql = "\n".join(
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if not line.strip().startswith("--")
        )
        assert "ABS_DATA" not in executable_sql.upper()


def test_resource_monitor_contract_is_complete_and_non_replacing() -> None:
    sql = (SQL_DIRECTORY / "05_resource_monitor.sql").read_text(encoding="utf-8").upper()
    required_clauses = {
        "CREATE RESOURCE MONITOR IF NOT EXISTS RM_PHARMARETAIL_MONTHLY",
        "CREDIT_QUOTA = 20",
        "FREQUENCY = MONTHLY",
        "START_TIMESTAMP = IMMEDIATELY",
        "ON 50 PERCENT DO NOTIFY",
        "ON 75 PERCENT DO NOTIFY",
        "ON 90 PERCENT DO SUSPEND",
        "ON 100 PERCENT DO SUSPEND_IMMEDIATE",
        "RESOURCE_MONITOR = RM_PHARMARETAIL_MONTHLY",
    }
    assert all(clause in sql for clause in required_clauses)
    assert "CREATE OR REPLACE RESOURCE MONITOR" not in sql
