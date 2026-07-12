"""Create and grant the PHARMARETAIL INTERMEDIATE schema once, with checks."""

from __future__ import annotations

from scripts.deploy_snowflake import load_private_key_der
from scripts.validate_snowflake_config import SnowflakeConfig

EXPECTED_DATABASE = "PHARMARETAIL"
TARGET_SCHEMA = "INTERMEDIATE"
DBT_ROLE = "PHARMARETAIL_DBT"


def rows_as_dicts(cursor) -> list[dict[str, object]]:
    columns = [description[0].upper() for description in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def scalar(cursor, statement: str) -> int:
    cursor.execute(statement)
    value = cursor.fetchone()[0]
    return int(value)


def verify_foundation(cursor) -> None:
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

    print(
        "foundation_database=PHARMARETAIL verified "
        f"databases={len(database_names)} raw_tables={len(raw_objects)} "
        f"staging_tables={len(staging_tables)} staging_views={len(staging_views)}"
    )


def apply_grants(cursor) -> None:
    cursor.execute("CREATE SCHEMA IF NOT EXISTS PHARMARETAIL.INTERMEDIATE")
    cursor.execute("GRANT USAGE ON DATABASE PHARMARETAIL TO ROLE PHARMARETAIL_DBT")
    cursor.execute(
        "GRANT USAGE ON SCHEMA PHARMARETAIL.INTERMEDIATE TO ROLE PHARMARETAIL_DBT"
    )
    cursor.execute(
        "GRANT CREATE VIEW ON SCHEMA PHARMARETAIL.INTERMEDIATE TO ROLE PHARMARETAIL_DBT"
    )
    cursor.execute(
        "GRANT CREATE TABLE ON SCHEMA PHARMARETAIL.INTERMEDIATE TO ROLE PHARMARETAIL_DBT"
    )


def verify_grants(cursor) -> None:
    cursor.execute("SHOW GRANTS TO ROLE PHARMARETAIL_DBT")
    grants = rows_as_dicts(cursor)
    required = {
        ("USAGE", "DATABASE", "PHARMARETAIL"),
        ("USAGE", "SCHEMA", "PHARMARETAIL.INTERMEDIATE"),
        ("CREATE VIEW", "SCHEMA", "PHARMARETAIL.INTERMEDIATE"),
        ("CREATE TABLE", "SCHEMA", "PHARMARETAIL.INTERMEDIATE"),
    }
    actual = {
        (
            str(row.get("PRIVILEGE", "")).upper(),
            str(row.get("GRANTED_ON", "")).upper(),
            str(row.get("NAME", "")).upper(),
        )
        for row in grants
    }
    missing = sorted(required - actual)
    if missing:
        raise RuntimeError(f"Required PHARMARETAIL_DBT grants are missing: {missing}")
    print("intermediate_schema=PHARMARETAIL.INTERMEDIATE created_or_verified")
    print("grants=USAGE(database),USAGE(schema),CREATE VIEW,CREATE TABLE verified")


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
        "session_parameters": {"QUERY_TAG": "PHARMARETAIL_INTERMEDIATE_SCHEMA_REPAIR"},
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
