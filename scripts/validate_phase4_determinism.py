"""Regenerate Phase 4 dbt models and compare stable Snowflake fingerprints."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Mapping

import snowflake.connector

from scripts.deploy_snowflake import load_private_key_der

MODELS = (
    "DIM_SUPPLIER",
    "FCT_INVENTORY_SNAPSHOT",
    "FCT_SUPPLIER_DELIVERY",
    "FCT_STOCKOUT_EVENT",
    "FCT_PROMOTION",
    "FCT_INCIDENT",
)


def connection_kwargs(environment: Mapping[str, str]) -> dict[str, object]:
    required = (
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_DBT_USER",
        "SNOWFLAKE_PRIVATE_KEY",
        "SNOWFLAKE_DATABASE",
        "SNOWFLAKE_WAREHOUSE",
    )
    missing = [name for name in required if not environment.get(name, "").strip()]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    return {
        "account": environment["SNOWFLAKE_ACCOUNT"],
        "user": environment["SNOWFLAKE_DBT_USER"],
        "private_key": load_private_key_der(
            environment["SNOWFLAKE_PRIVATE_KEY"],
            environment.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE") or None,
        ),
        "role": "PHARMARETAIL_DBT",
        "warehouse": environment["SNOWFLAKE_WAREHOUSE"],
        "database": environment["SNOWFLAKE_DATABASE"],
        "session_parameters": {"QUERY_TAG": "PHARMARETAIL_PHASE4_DETERMINISM"},
    }


def fingerprints(connection: snowflake.connector.SnowflakeConnection) -> dict[str, tuple[int, str]]:
    database = os.environ["SNOWFLAKE_DATABASE"]
    result: dict[str, tuple[int, str]] = {}
    cursor = connection.cursor()
    try:
        for model in MODELS:
            cursor.execute(f"SELECT COUNT(*), HASH_AGG(*) FROM {database}.MARTS.{model}")
            row_count, fingerprint = cursor.fetchone()
            result[model] = (int(row_count), str(fingerprint))
    finally:
        cursor.close()
    return result


def main() -> int:
    dbt = shutil.which("dbt")
    if not dbt:
        raise RuntimeError("dbt executable was not found")
    connection = snowflake.connector.connect(**connection_kwargs(os.environ))
    try:
        before = fingerprints(connection)
        subprocess.run([dbt, "run", "--select", "tag:phase4"], check=True)  # noqa: S603
        after = fingerprints(connection)
    finally:
        connection.close()
    if before != after:
        changed = sorted(name for name in MODELS if before[name] != after[name])
        raise AssertionError(f"Deterministic regeneration mismatch: {', '.join(changed)}")
    for model, (row_count, fingerprint) in sorted(after.items()):
        print(f"deterministic_model={model} rows={row_count} fingerprint={fingerprint}")
    print("phase4_deterministic_regeneration=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
