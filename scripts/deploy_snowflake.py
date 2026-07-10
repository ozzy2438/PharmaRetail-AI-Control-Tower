"""Execute ordered Snowflake foundation SQL using environment-only credentials."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.validate_snowflake_config import SnowflakeConfig

DEFAULT_SQL_DIRECTORY = Path("infra/snowflake")


def discover_scripts(directory: Path) -> list[Path]:
    return sorted(path for path in directory.glob("[0-9][0-9]_*.sql") if path.is_file())


def validate_scripts(scripts: list[Path]) -> None:
    if not scripts:
        raise ValueError("No ordered Snowflake SQL scripts were found")
    names = [path.name for path in scripts]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate Snowflake SQL script names were found")
    for path in scripts:
        sql = path.read_text(encoding="utf-8")
        if not sql.strip():
            raise ValueError(f"SQL script is empty: {path}")


def load_private_key_der(pem_text: str, passphrase: str | None) -> bytes:
    """Convert a PEM private key (optionally encrypted) to unencrypted PKCS8 DER bytes."""
    from cryptography.hazmat.primitives import serialization

    private_key = serialization.load_pem_private_key(
        pem_text.encode("utf-8"),
        password=passphrase.encode("utf-8") if passphrase else None,
    )
    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def execute_scripts(config: SnowflakeConfig, scripts: list[Path]) -> None:
    import snowflake.connector

    connect_kwargs: dict[str, object] = {
        "account": config.account,
        "user": config.user,
        "role": config.role,
        "session_parameters": {"QUERY_TAG": "PHARMARETAIL_FOUNDATION_DEPLOY"},
    }
    if config.auth_method == "key_pair":
        connect_kwargs["private_key"] = load_private_key_der(
            config.private_key_pem, config.private_key_passphrase
        )
    else:
        connect_kwargs["password"] = config.password

    connection = snowflake.connector.connect(**connect_kwargs)
    try:
        for path in scripts:
            print(f"Executing {path}")
            sql = path.read_text(encoding="utf-8")
            for cursor in connection.execute_string(sql):
                cursor.close()
        print("Snowflake foundation deployment completed.")
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sql-directory", type=Path, default=DEFAULT_SQL_DIRECTORY)
    parser.add_argument(
        "--script",
        action="append",
        type=Path,
        dest="scripts",
        help="Execute only this SQL script; may be supplied more than once.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = SnowflakeConfig.from_environment()
    config.validate()
    scripts = args.scripts if args.scripts else discover_scripts(args.sql_directory)
    validate_scripts(scripts)
    print(f"Validated {len(scripts)} ordered Snowflake SQL scripts.")
    if args.dry_run:
        print("Dry run completed; no Snowflake connection or mutation occurred.")
        return 0

    try:
        execute_scripts(config, scripts)
    except Exception as exc:
        print(f"Deployment failed: {type(exc).__name__}. Review the preceding safe error output.")
        print("Rollback is not automatic. Follow infra/snowflake/rollback.sql and the runbook.")
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
