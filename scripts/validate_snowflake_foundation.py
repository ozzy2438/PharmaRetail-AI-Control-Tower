"""Validate Snowflake foundation objects and least-privilege role boundaries."""

from __future__ import annotations

from collections.abc import Callable

import snowflake.connector
from snowflake.connector.errors import ProgrammingError

from scripts.validate_snowflake_config import SnowflakeConfig

DATABASE = "PHARMARETAIL_AI_CONTROL_TOWER"
WAREHOUSE = "WH_PHARMARETAIL"
RESOURCE_MONITOR = "RM_PHARMARETAIL_MONTHLY"
PROJECT_SCHEMAS = {"RAW", "STAGING", "INTERMEDIATE", "MARTS", "GOVERNANCE", "AI_LOGS"}
PROJECT_ROLES = {
    "PHARMARETAIL_ADMIN",
    "PHARMARETAIL_ENGINEER",
    "PHARMARETAIL_DBT",
    "PHARMARETAIL_AI_APP",
    "PHARMARETAIL_READONLY",
}


def as_boolean(value: object) -> bool:
    return value is True or str(value).strip().lower() == "true"


def rows_as_dicts(cursor: snowflake.connector.cursor.SnowflakeCursor) -> list[dict]:
    columns = [item[0].lower() for item in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def expect_denied(cursor: snowflake.connector.cursor.SnowflakeCursor, sql: str) -> None:
    try:
        cursor.execute(sql)
    except ProgrammingError:
        return
    raise AssertionError(f"Expected access denial but statement succeeded: {sql}")


def use_project_role(
    cursor: snowflake.connector.cursor.SnowflakeCursor,
    role: str,
) -> None:
    cursor.execute(f"USE ROLE {role}")
    cursor.execute("USE SECONDARY ROLES NONE")
    cursor.execute(f"USE WAREHOUSE {WAREHOUSE}")
    cursor.execute(f"USE DATABASE {DATABASE}")


def validate_structure(cursor: snowflake.connector.cursor.SnowflakeCursor) -> None:
    cursor.execute(f"SHOW WAREHOUSES LIKE '{WAREHOUSE}'")
    warehouses = rows_as_dicts(cursor)
    if len(warehouses) != 1:
        raise AssertionError("Expected exactly one project warehouse")
    warehouse = warehouses[0]
    if str(warehouse["size"]).upper() not in {"X-SMALL", "XSMALL"}:
        raise AssertionError("Warehouse must remain XSMALL")
    if int(warehouse["auto_suspend"]) != 60:
        raise AssertionError("Warehouse auto-suspend must remain 60 seconds")
    if not as_boolean(warehouse["auto_resume"]):
        raise AssertionError("Warehouse auto-resume must be enabled")
    if warehouse["resource_monitor"] != RESOURCE_MONITOR:
        raise AssertionError("Warehouse resource monitor assignment is missing")
    print("structure_warehouse=PASS")

    cursor.execute(f"SHOW SCHEMAS IN DATABASE {DATABASE}")
    schema_names = {row["name"] for row in rows_as_dicts(cursor)}
    if not PROJECT_SCHEMAS.issubset(schema_names):
        raise AssertionError("One or more project schemas are missing")
    if "PUBLIC" in schema_names:
        raise AssertionError("Dedicated project database must not contain PUBLIC schema")
    print("structure_schemas=PASS count=6")

    cursor.execute("SHOW ROLES LIKE 'PHARMARETAIL_%'")
    role_names = {row["name"] for row in rows_as_dicts(cursor)}
    if role_names != PROJECT_ROLES:
        raise AssertionError("Project role inventory differs from the contract")
    print("structure_roles=PASS count=5")

    cursor.execute(f"SHOW RESOURCE MONITORS LIKE '{RESOURCE_MONITOR}'")
    monitors = rows_as_dicts(cursor)
    if len(monitors) != 1:
        raise AssertionError("Expected exactly one project resource monitor")
    monitor = monitors[0]
    if float(monitor["credit_quota"]) != 20:
        raise AssertionError("Resource monitor quota must remain 20 credits")
    if str(monitor["frequency"]).upper() != "MONTHLY":
        raise AssertionError("Resource monitor frequency must remain monthly")
    if str(monitor["level"]).upper() != "WAREHOUSE":
        raise AssertionError("Resource monitor must remain assigned at warehouse level")
    notify_thresholds = {
        item.strip() for item in str(monitor["notify_at"]).split(",") if item.strip()
    }
    if notify_thresholds != {"50%", "75%"}:
        raise AssertionError("Resource monitor notify thresholds must remain at 50% and 75%")
    if str(monitor["suspend_at"]).strip() != "90%":
        raise AssertionError("Resource monitor suspend threshold must remain at 90%")
    if str(monitor["suspend_immediately_at"]).strip() != "100%":
        raise AssertionError("Resource monitor immediate-suspend threshold must remain at 100%")
    print("structure_resource_monitor=PASS")

    expected_future_grant_counts = {
        "PHARMARETAIL_ENGINEER": 24,
        "PHARMARETAIL_DBT": 20,
        "PHARMARETAIL_AI_APP": 5,
        "PHARMARETAIL_READONLY": 2,
    }
    total_grants = 0
    for role, expected_count in expected_future_grant_counts.items():
        cursor.execute(f"SHOW FUTURE GRANTS TO ROLE {role}")
        grants = rows_as_dicts(cursor)
        if len(grants) != expected_count:
            raise AssertionError(
                f"Future-grant count differs for {role}: {len(grants)} != {expected_count}"
            )
        total_grants += len(grants)
    print(f"structure_future_grants=PASS count={total_grants}")


def create_fixtures(cursor: snowflake.connector.cursor.SnowflakeCursor) -> None:
    use_project_role(cursor, "PHARMARETAIL_ADMIN")
    statements = (
        f"CREATE OR REPLACE TABLE {DATABASE}.RAW.__FOUNDATION_SMOKE_RAW (ID INTEGER)",
        f"INSERT INTO {DATABASE}.RAW.__FOUNDATION_SMOKE_RAW VALUES (1)",
        f"CREATE OR REPLACE TABLE {DATABASE}.MARTS.__FOUNDATION_SMOKE_MART (ID INTEGER)",
        f"INSERT INTO {DATABASE}.MARTS.__FOUNDATION_SMOKE_MART VALUES (1)",
        f"CREATE OR REPLACE TABLE {DATABASE}.GOVERNANCE.__FOUNDATION_SMOKE_REF (ID INTEGER)",
        f"INSERT INTO {DATABASE}.GOVERNANCE.__FOUNDATION_SMOKE_REF VALUES (1)",
        (
            f"CREATE OR REPLACE TABLE {DATABASE}.AI_LOGS.__FOUNDATION_SMOKE_LOG "
            "(EVENT_NAME VARCHAR)"
        ),
    )
    for statement in statements:
        cursor.execute(statement)


def run_role_smoke_tests(cursor: snowflake.connector.cursor.SnowflakeCursor) -> None:
    use_project_role(cursor, "PHARMARETAIL_ENGINEER")
    cursor.execute(
        f"CREATE OR REPLACE TABLE {DATABASE}.RAW.__FOUNDATION_ENGINEER_CREATE (ID INTEGER)"
    )
    cursor.execute(f"DROP TABLE {DATABASE}.RAW.__FOUNDATION_ENGINEER_CREATE")
    print("smoke_engineer_raw_create=PASS")

    use_project_role(cursor, "PHARMARETAIL_READONLY")
    cursor.execute(f"SELECT COUNT(*) FROM {DATABASE}.MARTS.__FOUNDATION_SMOKE_MART")
    expect_denied(cursor, f"SELECT * FROM {DATABASE}.RAW.__FOUNDATION_SMOKE_RAW")
    print("smoke_readonly_marts_select=PASS raw_denied=PASS")

    use_project_role(cursor, "PHARMARETAIL_AI_APP")
    cursor.execute(f"SELECT COUNT(*) FROM {DATABASE}.MARTS.__FOUNDATION_SMOKE_MART")
    cursor.execute(f"SELECT COUNT(*) FROM {DATABASE}.GOVERNANCE.__FOUNDATION_SMOKE_REF")
    cursor.execute(
        f"INSERT INTO {DATABASE}.AI_LOGS.__FOUNDATION_SMOKE_LOG VALUES ('smoke-test')"
    )
    expect_denied(cursor, f"SELECT * FROM {DATABASE}.RAW.__FOUNDATION_SMOKE_RAW")
    print("smoke_ai_app_curated_read_log_write=PASS raw_denied=PASS")

    use_project_role(cursor, "PHARMARETAIL_DBT")
    cursor.execute(f"SELECT COUNT(*) FROM {DATABASE}.RAW.__FOUNDATION_SMOKE_RAW")
    cursor.execute(
        f"CREATE OR REPLACE TABLE {DATABASE}.STAGING.__FOUNDATION_DBT_CREATE (ID INTEGER)"
    )
    cursor.execute(f"DROP TABLE {DATABASE}.STAGING.__FOUNDATION_DBT_CREATE")
    expect_denied(
        cursor,
        f"CREATE TABLE {DATABASE}.RAW.__FOUNDATION_DBT_DENIED (ID INTEGER)",
    )
    print("smoke_dbt_staging_create=PASS raw_create_denied=PASS")


def cleanup(cursor: snowflake.connector.cursor.SnowflakeCursor) -> None:
    cursor.execute("USE ROLE PHARMARETAIL_ADMIN")
    cursor.execute("USE SECONDARY ROLES NONE")
    for name in (
        f"{DATABASE}.RAW.__FOUNDATION_SMOKE_RAW",
        f"{DATABASE}.RAW.__FOUNDATION_ENGINEER_CREATE",
        f"{DATABASE}.RAW.__FOUNDATION_DBT_DENIED",
        f"{DATABASE}.STAGING.__FOUNDATION_DBT_CREATE",
        f"{DATABASE}.MARTS.__FOUNDATION_SMOKE_MART",
        f"{DATABASE}.GOVERNANCE.__FOUNDATION_SMOKE_REF",
        f"{DATABASE}.AI_LOGS.__FOUNDATION_SMOKE_LOG",
    ):
        cursor.execute(f"DROP TABLE IF EXISTS {name}")
    cursor.execute(f"ALTER WAREHOUSE IF EXISTS {WAREHOUSE} SUSPEND")
    print("smoke_cleanup=PASS warehouse_suspended=true")


def with_cleanup(
    cursor: snowflake.connector.cursor.SnowflakeCursor,
    operation: Callable[[snowflake.connector.cursor.SnowflakeCursor], None],
) -> None:
    try:
        operation(cursor)
    finally:
        cleanup(cursor)


def main() -> int:
    config = SnowflakeConfig.from_environment()
    config.validate()
    connection = snowflake.connector.connect(
        account=config.account,
        user=config.user,
        password=config.password,
        role=config.role,
        session_parameters={"QUERY_TAG": "PHARMARETAIL_FOUNDATION_SMOKE_TEST"},
    )
    try:
        cursor = connection.cursor()
        validate_structure(cursor)
        create_fixtures(cursor)
        with_cleanup(cursor, run_role_smoke_tests)
    finally:
        connection.close()
    print("foundation_validation=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
