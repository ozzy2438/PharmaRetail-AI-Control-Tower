"""Create and grant the fixed PHARMARETAIL dbt schemas once, with checks."""

from __future__ import annotations

from scripts.deploy_snowflake import load_private_key_der
from scripts.validate_snowflake_config import SnowflakeConfig

EXPECTED_DATABASE = "PHARMARETAIL"
DBT_ROLE = "PHARMARETAIL_DBT"
MODEL_SCHEMAS = ("STAGING", "INTERMEDIATE", "MARTS")
STAGING_VIEW_MODELS = (
    "STG_PRODUCT",
    "STG_STORE",
    "STG_UCI_INVALID_PRICE",
    "STG_UCI_RETURNS",
    "STG_UCI_SALES",
)


def rows_as_dicts(cursor) -> list[dict[str, object]]:
    columns = [description[0].upper() for description in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def verify_foundation(cursor) -> tuple[set[str], set[str]]:
    cursor.execute("SHOW DATABASES")
    databases = rows_as_dicts(cursor)
    database_names = {str(row.get("NAME", "")).upper() for row in databases}
    if EXPECTED_DATABASE not in database_names:
        raise RuntimeError(
            f"Required database {EXPECTED_DATABASE} was not returned by SHOW DATABASES"
        )

    cursor.execute("SHOW TABLES IN SCHEMA PHARMARETAIL.RAW")
    raw_objects = rows_as_dicts(cursor)
    cursor.execute("SHOW TABLES IN SCHEMA PHARMARETAIL.STAGING")
    staging_tables = rows_as_dicts(cursor)
    cursor.execute("SHOW VIEWS IN SCHEMA PHARMARETAIL.STAGING")
    staging_views = rows_as_dicts(cursor)
    if not raw_objects:
        raise RuntimeError("PHARMARETAIL.RAW has no visible tables")
    if not staging_tables and not staging_views:
        raise RuntimeError("PHARMARETAIL.STAGING has no visible tables or views")
    staging_view_names = {
        str(row.get("NAME", "")).upper() for row in staging_views
    }
    missing_staging_views = sorted(set(STAGING_VIEW_MODELS) - staging_view_names)
    if missing_staging_views:
        raise RuntimeError(
            f"Required PHARMARETAIL.STAGING views are missing: {missing_staging_views}"
        )

    cursor.execute("SHOW SCHEMAS IN DATABASE PHARMARETAIL")
    schemas = rows_as_dicts(cursor)
    schema_names = {str(row.get("NAME", "")).upper() for row in schemas}

    print(
        "foundation_database=PHARMARETAIL verified "
        f"databases={len(database_names)} raw_tables={len(raw_objects)} "
        f"staging_tables={len(staging_tables)} staging_views={len(staging_views)} "
        f"visible_schemas={','.join(sorted(schema_names))}"
    )
    return schema_names, staging_view_names


def apply_grants(cursor) -> None:
    # These identifiers are intentionally fixed to the verified target. The
    # script refuses any other database before connecting, so no untrusted
    # input is interpolated into DDL/DCL.
    cursor.execute("GRANT USAGE ON DATABASE PHARMARETAIL TO ROLE PHARMARETAIL_DBT")
    for schema in MODEL_SCHEMAS:
        cursor.execute(
            f"CREATE SCHEMA IF NOT EXISTS PHARMARETAIL.{schema} WITH MANAGED ACCESS"
        )
        cursor.execute(
            f"GRANT USAGE ON SCHEMA PHARMARETAIL.{schema} TO ROLE PHARMARETAIL_DBT"
        )
        cursor.execute(
            f"GRANT CREATE VIEW ON SCHEMA PHARMARETAIL.{schema} TO ROLE PHARMARETAIL_DBT"
        )
        cursor.execute(
            f"GRANT CREATE TABLE ON SCHEMA PHARMARETAIL.{schema} TO ROLE PHARMARETAIL_DBT"
        )
    # These five views are dbt models but were bootstrapped by another role.
    # Transfer only their object ownership so full dbt deploy can replace them;
    # preserve existing consumer grants and never transfer schema ownership.
    for view_name in STAGING_VIEW_MODELS:
        cursor.execute(
            "GRANT OWNERSHIP ON VIEW "
            f"PHARMARETAIL.STAGING.{view_name} TO ROLE PHARMARETAIL_DBT "
            "COPY CURRENT GRANTS"
        )


def verify_grants(cursor) -> None:
    cursor.execute("SHOW GRANTS TO ROLE PHARMARETAIL_DBT")
    grants = rows_as_dicts(cursor)
    required = {("USAGE", "DATABASE", EXPECTED_DATABASE)}
    required.update(
        (privilege, "SCHEMA", schema)
        for schema in MODEL_SCHEMAS
        for privilege in ("USAGE", "CREATE VIEW", "CREATE TABLE")
    )
    required.update(("OWNERSHIP", "VIEW", view_name) for view_name in STAGING_VIEW_MODELS)
    actual = {
        (
            str(row.get("PRIVILEGE", "")).upper(),
            str(row.get("GRANTED_ON", "")).upper(),
            str(row.get("NAME", "")).strip('"').split(".")[-1].strip('"').upper(),
        )
        for row in grants
    }
    missing = sorted(required - actual)
    if missing:
        raise RuntimeError(f"Required PHARMARETAIL_DBT grants are missing: {missing}")
    print("dbt_schemas=PHARMARETAIL.STAGING,INTERMEDIATE,MARTS created_or_verified")
    print(
        "grants=USAGE(database),USAGE/CREATE VIEW/CREATE TABLE"
        "(staging,intermediate,marts),OWNERSHIP(five staging dbt views) verified"
    )


def main() -> int:
    import snowflake.connector

    config = SnowflakeConfig.from_environment()
    config.validate()
    if config.database != EXPECTED_DATABASE:
        raise ValueError(
            f"Refusing to switch databases: SNOWFLAKE_DATABASE must be {EXPECTED_DATABASE}, "
            f"got {config.database}"
        )
    if config.role != "ACCOUNTADMIN":
        raise ValueError(f"ACCOUNTADMIN is required for schema creation, got {config.role}")

    connect_kwargs: dict[str, object] = {
        "account": config.account,
        "user": config.user,
        "role": config.role,
        "warehouse": config.warehouse,
        "database": config.database,
        "session_parameters": {"QUERY_TAG": "PHARMARETAIL_DBT_SCHEMA_REPAIR"},
    }
    if config.auth_method == "key_pair":
        connect_kwargs["private_key"] = load_private_key_der(
            config.private_key_pem, config.private_key_passphrase
        )
    else:
        connect_kwargs["password"] = config.password

    connection = snowflake.connector.connect(**connect_kwargs)
    try:
        with connection.cursor() as cursor:
            cursor.execute("USE ROLE ACCOUNTADMIN")
            verify_foundation(cursor)
            apply_grants(cursor)
            verify_grants(cursor)
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
