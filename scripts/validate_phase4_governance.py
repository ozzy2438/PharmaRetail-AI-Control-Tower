"""Validate Phase 4 row access, masking, audit tagging, and future-grant isolation."""

from __future__ import annotations

import uuid

import snowflake.connector

from scripts.deploy_snowflake import load_private_key_der
from scripts.validate_snowflake_config import SnowflakeConfig

DATABASE = "PHARMARETAIL_AI_CONTROL_TOWER"
ASSIGNED_STORE = "CW_OSM_NODE_1247865789"
ASSIGNED_REGION = "VIC & TAS"
ACTIVE_DBT_KEY_FP = "SHA256:LL6crTqYxltfSP/w572ZpNs9ij3wbh5mySlcCk7fmp8="


def connect() -> snowflake.connector.SnowflakeConnection:
    config = SnowflakeConfig.from_environment()
    config.validate()
    kwargs: dict[str, object] = {
        "account": config.account,
        "user": config.user,
        "role": config.role,
        "warehouse": config.warehouse,
        "database": config.database,
        "session_parameters": {"QUERY_TAG": "PHARMARETAIL_PHASE4_GOVERNANCE_TEST"},
    }
    if config.private_key_pem:
        kwargs["private_key"] = load_private_key_der(
            config.private_key_pem, config.private_key_passphrase
        )
    else:
        kwargs["password"] = config.password
    return snowflake.connector.connect(**kwargs)


def scalar(cursor: snowflake.connector.cursor.SnowflakeCursor, sql: str) -> object:
    cursor.execute(sql)
    return cursor.fetchone()[0]


def use_role(cursor: snowflake.connector.cursor.SnowflakeCursor, role: str) -> None:
    cursor.execute(f"USE ROLE {role}")
    cursor.execute("USE SECONDARY ROLES NONE")
    cursor.execute("ALTER SESSION SET QUERY_TAG = 'PHARMARETAIL_PHASE4_GOVERNANCE_TEST'")


def validate_row_access(cursor: snowflake.connector.cursor.SnowflakeCursor) -> None:
    use_role(cursor, "PHARMARETAIL_STORE_MANAGER")
    stores = scalar(
        cursor,
        f"SELECT COUNT(DISTINCT STORE_ID) FROM {DATABASE}.MARTS.FCT_INVENTORY_SNAPSHOT",
    )
    leakage = scalar(
        cursor,
        f"SELECT COUNT(*) FROM {DATABASE}.MARTS.FCT_INVENTORY_SNAPSHOT "
        f"WHERE STORE_ID <> '{ASSIGNED_STORE}'",
    )
    if stores != 1 or leakage != 0:
        raise AssertionError("Store-manager RLS leakage detected")

    use_role(cursor, "PHARMARETAIL_AREA_MANAGER")
    leakage = scalar(
        cursor,
        f"SELECT COUNT(*) FROM {DATABASE}.MARTS.FCT_INVENTORY_SNAPSHOT "
        f"WHERE REGION <> '{ASSIGNED_REGION}'",
    )
    if leakage != 0:
        raise AssertionError("Area-manager RLS leakage detected")

    use_role(cursor, "PHARMARETAIL_SUPPLY_CHAIN_ANALYST")
    stores = scalar(
        cursor,
        f"SELECT COUNT(DISTINCT STORE_ID) FROM {DATABASE}.MARTS.FCT_INVENTORY_SNAPSHOT",
    )
    if stores != 100:
        raise AssertionError(f"National role expected 100 stores, received {stores}")
    print("phase4_rls_leakage=PASS rows=0")


def validate_masking(cursor: snowflake.connector.cursor.SnowflakeCursor) -> None:
    use_role(cursor, "PHARMARETAIL_STORE_MANAGER")
    email = scalar(cursor, f"SELECT MIN(CONTACT_EMAIL) FROM {DATABASE}.MARTS.DIM_SUPPLIER")
    root_cause = scalar(
        cursor,
        f"SELECT MIN(GROUND_TRUTH_ROOT_CAUSE) FROM {DATABASE}.MARTS.FCT_INVENTORY_SNAPSHOT",
    )
    if email != "***MASKED***" or root_cause != "***MASKED***":
        raise AssertionError("Sensitive text masking failed")
    print("phase4_masking=PASS")


def validate_future_grants(cursor: snowflake.connector.cursor.SnowflakeCursor) -> None:
    use_role(cursor, "PHARMARETAIL_ADMIN")
    for role in ("PHARMARETAIL_STORE_MANAGER", "PHARMARETAIL_AREA_MANAGER"):
        cursor.execute(f"SHOW FUTURE GRANTS TO ROLE {role}")
        if cursor.fetchall():
            raise AssertionError(f"Unexpected future grant for {role}")
    cursor.execute("SHOW FUTURE GRANTS TO ROLE PHARMARETAIL_AI_APP")
    columns = [column[0].lower() for column in cursor.description]
    grants = [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
    leaked = [
        grant
        for grant in grants
        if grant.get("grant_on") in {"TABLE", "VIEW"}
        and str(grant.get("name", "")).upper().endswith(".MARTS.<TABLE>")
    ]
    if leaked:
        raise AssertionError("AI_APP retains a broad MARTS future grant")
    print("phase4_future_grants=PASS")


def validate_security_closure(cursor: snowflake.connector.cursor.SnowflakeCursor) -> None:
    use_role(cursor, "PHARMARETAIL_ADMIN")
    cursor.execute(
        f"SELECT RSA_PUBLIC_KEY_FP, RSA_PUBLIC_KEY_2_FP FROM "
        f"{DATABASE}.GOVERNANCE.SECURITY_CLOSURE_EVIDENCE "
        "WHERE USER_NAME = 'SVC_PHARMARETAIL_DBT'"
    )
    row = cursor.fetchone()
    if row is None or row[0] != ACTIVE_DBT_KEY_FP or row[1] is not None:
        raise AssertionError("DBT key rotation evidence does not match the active-key contract")
    print("phase3_retired_key_invalidation=PASS")


def validate_audit(cursor: snowflake.connector.cursor.SnowflakeCursor) -> None:
    use_role(cursor, "PHARMARETAIL_AI_APP")
    audit_id = str(uuid.uuid4())
    cursor.execute(
        f"INSERT INTO {DATABASE}.AI_LOGS.OPERATIONAL_ACCESS_AUDIT "
        "(AUDIT_ID, EVENT_TIMESTAMP, ACTOR, ACTIVE_ROLE, QUERY_TAG, ACTION_NAME, "
        "OBJECT_NAME, ROW_COUNT, OUTCOME) "
        "SELECT %s, CURRENT_TIMESTAMP(), CURRENT_USER(), CURRENT_ROLE(), "
        "'PHARMARETAIL_PHASE4_GOVERNANCE_TEST', "
        "%s, %s, %s, %s",
        (audit_id, "RLS_SMOKE_TEST", "MARTS.FCT_INVENTORY_SNAPSHOT", 0, "PASS"),
    )
    tagged = scalar(
        cursor,
        "SELECT COUNT(*) FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION()) "
        "WHERE QUERY_TAG = 'PHARMARETAIL_PHASE4_GOVERNANCE_TEST'",
    )
    if not tagged:
        raise AssertionError("Tagged query was not visible in session query history")
    print("phase4_audit_query_tagging=PASS")


def main() -> int:
    connection = connect()
    try:
        cursor = connection.cursor()
        validate_row_access(cursor)
        validate_masking(cursor)
        validate_future_grants(cursor)
        validate_security_closure(cursor)
        validate_audit(cursor)
    finally:
        connection.close()
    print("phase4_governance_validation=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
