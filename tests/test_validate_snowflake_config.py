from __future__ import annotations

import pytest

from scripts.validate_snowflake_config import REQUIRED_VARIABLES, SnowflakeConfig

VALID_ENV = {
    "SNOWFLAKE_ACCOUNT": "ORG-ACCOUNT",
    "SNOWFLAKE_USER": "CI_USER",
    "SNOWFLAKE_PASSWORD": "not-a-real-secret",
    "SNOWFLAKE_ROLE": "ACCOUNTADMIN",
    "SNOWFLAKE_WAREHOUSE": "WH_PHARMARETAIL",
    "SNOWFLAKE_DATABASE": "PHARMARETAIL_AI_CONTROL_TOWER",
}


def test_config_loads_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in VALID_ENV.items():
        monkeypatch.setenv(name, value)
    config = SnowflakeConfig.from_environment()
    config.validate()
    assert config.account == "ORG-ACCOUNT"


def test_missing_variables_are_reported_without_values(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in REQUIRED_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError, match="SNOWFLAKE_PASSWORD") as exc_info:
        SnowflakeConfig.from_environment()
    assert "not-a-real-secret" not in str(exc_info.value)


def test_account_url_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in VALID_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "example.snowflakecomputing.com")
    with pytest.raises(ValueError, match="account identifier"):
        SnowflakeConfig.from_environment().validate()
