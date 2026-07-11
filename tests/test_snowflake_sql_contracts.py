from __future__ import annotations

import re
from pathlib import Path

import yaml

from scripts.load_raw_data import DATASET_TABLES

SQL_DIRECTORY = Path("infra/snowflake")
AUDIT_COLUMNS = {"_LOAD_ID", "_LOADED_AT", "_SOURCE_FILE"}


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


def _raw_table_columns() -> dict[str, list[str]]:
    sql = (SQL_DIRECTORY / "08_raw_tables.sql").read_text(encoding="utf-8")
    tables = re.findall(r"CREATE TABLE IF NOT EXISTS (RAW\.\w+) \((.*?)\n\)", sql, re.S)
    return {
        name: [line.strip().split()[0] for line in body.splitlines() if line.strip()]
        for name, body in tables
    }


def test_raw_tables_match_contract_columns() -> None:
    ddl_columns = _raw_table_columns()
    for contract_path_str, table in DATASET_TABLES.items():
        contract = yaml.safe_load(Path(contract_path_str).read_text(encoding="utf-8"))
        expected = {column["name"].upper() for column in contract["columns"]}
        actual = set(ddl_columns[table]) - AUDIT_COLUMNS
        assert actual == expected, f"{table} columns diverge from {contract_path_str}"


def test_raw_tables_include_audit_columns() -> None:
    ddl_columns = _raw_table_columns()
    for table in DATASET_TABLES.values():
        assert AUDIT_COLUMNS.issubset(ddl_columns[table]), f"{table} missing audit columns"
