"""Validate Snowflake connection configuration without printing secret values."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

REQUIRED_VARIABLES = (
    "SNOWFLAKE_ACCOUNT",
    "SNOWFLAKE_USER",
    "SNOWFLAKE_ROLE",
    "SNOWFLAKE_WAREHOUSE",
    "SNOWFLAKE_DATABASE",
)

# Exactly one of these authentication paths must be provided. Key-pair auth is
# used by the SVC_PHARMARETAIL_CICD service identity for BAU deployments;
# password auth remains for the human-gated ACCOUNTADMIN bootstrap path.
AUTH_VARIABLES = ("SNOWFLAKE_PASSWORD", "SNOWFLAKE_PRIVATE_KEY")


@dataclass(frozen=True)
class SnowflakeConfig:
    account: str
    user: str
    role: str
    warehouse: str
    database: str
    password: str | None = None
    private_key_pem: str | None = None
    private_key_passphrase: str | None = None

    @property
    def auth_method(self) -> str:
        return "key_pair" if self.private_key_pem else "password"

    @classmethod
    def from_environment(cls) -> "SnowflakeConfig":
        missing = [name for name in REQUIRED_VARIABLES if not os.getenv(name, "").strip()]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        password = os.getenv("SNOWFLAKE_PASSWORD") or None
        private_key_pem = os.getenv("SNOWFLAKE_PRIVATE_KEY") or None
        if not password and not private_key_pem:
            raise ValueError(
                f"Missing required environment variables: one of {', '.join(AUTH_VARIABLES)}"
            )
        return cls(
            account=os.environ["SNOWFLAKE_ACCOUNT"].strip(),
            user=os.environ["SNOWFLAKE_USER"].strip(),
            role=os.environ["SNOWFLAKE_ROLE"].strip(),
            warehouse=os.environ["SNOWFLAKE_WAREHOUSE"].strip(),
            database=os.environ["SNOWFLAKE_DATABASE"].strip(),
            password=password,
            private_key_pem=private_key_pem,
            private_key_passphrase=os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE") or None,
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
