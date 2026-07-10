"""Validate Snowflake connection configuration without printing secret values."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

REQUIRED_VARIABLES = (
    "SNOWFLAKE_ACCOUNT",
    "SNOWFLAKE_USER",
    "SNOWFLAKE_PASSWORD",
    "SNOWFLAKE_ROLE",
    "SNOWFLAKE_WAREHOUSE",
    "SNOWFLAKE_DATABASE",
)


@dataclass(frozen=True)
class SnowflakeConfig:
    account: str
    user: str
    password: str
    role: str
    warehouse: str
    database: str

    @classmethod
    def from_environment(cls) -> "SnowflakeConfig":
        missing = [name for name in REQUIRED_VARIABLES if not os.getenv(name, "").strip()]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        return cls(
            account=os.environ["SNOWFLAKE_ACCOUNT"].strip(),
            user=os.environ["SNOWFLAKE_USER"].strip(),
            password=os.environ["SNOWFLAKE_PASSWORD"],
            role=os.environ["SNOWFLAKE_ROLE"].strip(),
            warehouse=os.environ["SNOWFLAKE_WAREHOUSE"].strip(),
            database=os.environ["SNOWFLAKE_DATABASE"].strip(),
        )

    def validate(self) -> None:
        if ".snowflakecomputing.com" in self.account:
            raise ValueError("SNOWFLAKE_ACCOUNT must be an account identifier, not an account URL")
        if self.role.upper() != self.role:
            raise ValueError("SNOWFLAKE_ROLE must use an explicit uppercase role identifier")
        if self.warehouse.upper() != self.warehouse:
            raise ValueError("SNOWFLAKE_WAREHOUSE must use an explicit uppercase identifier")
        if self.database.upper() != self.database:
            raise ValueError("SNOWFLAKE_DATABASE must use an explicit uppercase identifier")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-connect",
        action="store_true",
        help="Validate configuration shape only; no network connection is attempted.",
    )
    args = parser.parse_args()
    config = SnowflakeConfig.from_environment()
    config.validate()
    if not args.no_connect:
        raise SystemExit("Connection attempts are performed by deploy_snowflake.py")
    print("Snowflake configuration validation passed; secret values were not logged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
