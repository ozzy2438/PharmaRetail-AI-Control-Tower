from __future__ import annotations

import re
from pathlib import Path

import yaml

from scripts.load_raw_data import DATASET_TABLES

SQL_DIRECTORY = Path("infra/snowflake")
AUDIT_COLUMNS = {"_LOAD_ID", "_LOADED_AT", "_SOURCE_FILE"}
DATABASE = "PHARMARETAIL_AI_CONTROL_TOWER"
LIVE_DBT_DATABASE = "PHARMARETAIL"


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
    tables = re.findall(
        rf"CREATE TABLE IF NOT EXISTS ({re.escape(DATABASE)}\.RAW\.\w+) \((.*?)\n\)", sql, re.S
    )
    return {
        name: [line.strip().split()[0] for line in body.splitlines() if line.strip()]
        for name, body in tables
    }


def _qualify(table: str) -> str:
    # DATASET_TABLES values are schema-qualified only (e.g. "RAW.UCI_SALES");
    # the DDL is database-qualified too (e.g. "PHARMARETAIL_AI_CONTROL_TOWER.RAW.UCI_SALES").
    return f"{DATABASE}.{table}"


def test_raw_tables_are_fully_qualified() -> None:
    # 08_raw_tables.sql runs via deploy_snowflake.py, whose connection does not
    # set an explicit database, so unqualified RAW.<object> names would resolve
    # against whatever database happens to be current for the connecting
    # identity. Every object must be fully qualified to avoid that ambiguity.
    ddl_columns = _raw_table_columns()
    for table in DATASET_TABLES.values():
        assert _qualify(table) in ddl_columns, f"{table} is not fully qualified"


def test_raw_tables_match_contract_columns() -> None:
    ddl_columns = _raw_table_columns()
    for contract_path_str, table in DATASET_TABLES.items():
        contract = yaml.safe_load(Path(contract_path_str).read_text(encoding="utf-8"))
        expected = {column["name"].upper() for column in contract["columns"]}
        actual = set(ddl_columns[_qualify(table)]) - AUDIT_COLUMNS
        assert actual == expected, f"{table} columns diverge from {contract_path_str}"


def test_raw_tables_include_audit_columns() -> None:
    ddl_columns = _raw_table_columns()
    for table in DATASET_TABLES.values():
        actual = ddl_columns[_qualify(table)]
        assert AUDIT_COLUMNS.issubset(actual), f"{table} missing audit columns"


def test_phase4_persona_roles_and_policies_are_declared() -> None:
    roles = (SQL_DIRECTORY / "01_roles.sql").read_text(encoding="utf-8").upper()
    governance = (SQL_DIRECTORY / "10_phase4_governance.sql").read_text(
        encoding="utf-8"
    ).upper()
    for role in (
        "PHARMARETAIL_STORE_MANAGER",
        "PHARMARETAIL_AREA_MANAGER",
        "PHARMARETAIL_SUPPLY_CHAIN_ANALYST",
    ):
        assert f"CREATE ROLE IF NOT EXISTS {role}" in roles
    assert "CREATE ROW ACCESS POLICY IF NOT EXISTS" in governance
    assert "CREATE MASKING POLICY IF NOT EXISTS" in governance
    assert "USE SECONDARY ROLES" not in governance


def test_phase4_personas_never_receive_future_marts_select() -> None:
    grants = (SQL_DIRECTORY / "04_grants.sql").read_text(encoding="utf-8").upper()
    for role in ("PHARMARETAIL_STORE_MANAGER", "PHARMARETAIL_AREA_MANAGER"):
        pattern = re.compile(
            r"GRANT SELECT ON FUTURE (?:TABLES|VIEWS) IN SCHEMA "
            rf"{DATABASE}\.MARTS\s+TO ROLE {role}"
        )
        assert not pattern.search(grants)


def test_ai_app_broad_marts_access_is_revoked_before_explicit_grants() -> None:
    grants = (SQL_DIRECTORY / "phase4_model_grants.sql").read_text(encoding="utf-8").upper()
    revoke_position = grants.index("REVOKE SELECT ON ALL TABLES")
    explicit_position = grants.index(
        f"GRANT SELECT ON TABLE {LIVE_DBT_DATABASE}.MARTS.DIM_DATE"
    )
    assert revoke_position < explicit_position
    assert "REVOKE SELECT ON FUTURE TABLES" in grants
    assert "REVOKE SELECT ON FUTURE VIEWS" in grants


def test_supply_chain_analyst_receives_only_explicit_phase4_models() -> None:
    grants = (SQL_DIRECTORY / "phase4_model_grants.sql").read_text(encoding="utf-8").upper()
    role = "PHARMARETAIL_SUPPLY_CHAIN_ANALYST"
    assert (
        f"REVOKE SELECT ON ALL TABLES IN SCHEMA {LIVE_DBT_DATABASE}.MARTS\n"
        f"FROM ROLE {role}"
        in grants
    )
    assert not re.search(
        rf"GRANT SELECT ON ALL TABLES IN SCHEMA {LIVE_DBT_DATABASE}\.MARTS\s+"
        rf"TO ROLE {role}",
        grants,
    )
    for model in (
        "DIM_DATE",
        "DIM_STORE",
        "DIM_PRODUCT",
        "DIM_SUPPLIER",
        "FCT_INVENTORY_SNAPSHOT",
        "FCT_SUPPLIER_DELIVERY",
        "FCT_STOCKOUT_EVENT",
        "FCT_PROMOTION",
        "FCT_INCIDENT",
    ):
        assert (
            f"GRANT SELECT ON TABLE {LIVE_DBT_DATABASE}.MARTS.{model}\n"
            f"TO ROLE {role}"
            in grants
        )


def test_dbt_workflow_never_writes_private_key_to_github_env() -> None:
    workflow = Path(".github/workflows/dbt-run.yml").read_text(encoding="utf-8")
    assert "GITHUB_ENV" not in "\n".join(
        line for line in workflow.splitlines() if not line.lstrip().startswith("#")
    )


def test_dbt_governance_access_is_schema_resolution_only() -> None:
    grants = (SQL_DIRECTORY / "04_grants.sql").read_text(encoding="utf-8").upper()
    assert (
        f"GRANT USAGE ON SCHEMA {DATABASE}.GOVERNANCE\nTO ROLE PHARMARETAIL_DBT"
        in grants
    )
    statements = [statement.strip() for statement in grants.split(";")]
    assert not any(
        statement.startswith(("GRANT SELECT", "GRANT INSERT", "GRANT UPDATE", "GRANT DELETE"))
        and f"{DATABASE}.GOVERNANCE" in statement
        and "TO ROLE PHARMARETAIL_DBT" in statement
        for statement in statements
    )


def test_phase5_governed_rag_tables_and_least_privilege_grants_are_declared() -> None:
    rag_sql = (SQL_DIRECTORY / "11_phase5_rag.sql").read_text(encoding="utf-8").upper()
    for table in (
        "DOCUMENT_REGISTRY",
        "DOCUMENT_CHUNKS",
        "EMBEDDING_METADATA",
        "RETRIEVAL_AUDIT",
        "RAG_ROLE_ACCESS_SCOPE",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {DATABASE}.GOVERNANCE.{table}" in rag_sql
    assert (
        f"GRANT SELECT, INSERT ON TABLE {DATABASE}.GOVERNANCE.RETRIEVAL_AUDIT\n"
        "TO ROLE PHARMARETAIL_AI_APP"
    ) in rag_sql
    assert f"GRANT UPDATE ON TABLE {DATABASE}.GOVERNANCE.RETRIEVAL_AUDIT" not in rag_sql
    assert f"GRANT DELETE ON TABLE {DATABASE}.GOVERNANCE.RETRIEVAL_AUDIT" not in rag_sql
    assert "CHECK (EFFECTIVE_DATE <= EXPIRY_DATE)" in rag_sql
