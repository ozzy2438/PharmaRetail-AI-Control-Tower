from __future__ import annotations

import pytest

from scripts.validate_snowflake_config import AUTH_VARIABLES, REQUIRED_VARIABLES, SnowflakeConfig

VALID_ENV = {
    "SNOWFLAKE_ACCOUNT": "ORG-ACCOUNT",
    "SNOWFLAKE_USER": "CI_USER",
    "SNOWFLAKE_PASSWORD": "not-a-real-secret",
    "SNOWFLAKE_ROLE": "ACCOUNTADMIN",
    "SNOWFLAKE_WAREHOUSE": "WH_PHARMARETAIL",
    "SNOWFLAKE_DATABASE": "PHARMARETAIL_AI_CONTROL_TOWER",
}

VALID_KEY_PAIR_ENV = {
    "SNOWFLAKE_ACCOUNT": "ORG-ACCOUNT",
    "SNOWFLAKE_USER": "SVC_PHARMARETAIL_CICD",
    "SNOWFLAKE_PRIVATE_KEY": "not-a-real-private-key",
    "SNOWFLAKE_PRIVATE_KEY_PASSPHRASE": "not-a-real-passphrase",
    "SNOWFLAKE_ROLE": "PHARMARETAIL_ADMIN",
    "SNOWFLAKE_WAREHOUSE": "WH_PHARMARETAIL",
    "SNOWFLAKE_DATABASE": "PHARMARETAIL_AI_CONTROL_TOWER",
}


def _clear_auth_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in AUTH_VARIABLES + ("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE",):
        monkeypatch.delenv(name, raising=False)


def test_config_loads_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_auth_vars(monkeypatch)
    for name, value in VALID_ENV.items():
        monkeypatch.setenv(name, value)
    config = SnowflakeConfig.from_environment()
    config.validate()
    assert config.account == "ORG-ACCOUNT"
    assert config.auth_method == "password"


def test_key_pair_config_loads_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_auth_vars(monkeypatch)
    for name, value in VALID_KEY_PAIR_ENV.items():
        monkeypatch.setenv(name, value)
    config = SnowflakeConfig.from_environment()
    config.validate()
    assert config.auth_method == "key_pair"
    assert config.password is None


def test_missing_variables_are_reported_without_values(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (*REQUIRED_VARIABLES, *AUTH_VARIABLES, "SNOWFLAKE_PRIVATE_KEY_PASSPHRASE"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError, match="SNOWFLAKE_ACCOUNT") as exc_info:
        SnowflakeConfig.from_environment()
    assert "not-a-real-secret" not in str(exc_info.value)


def test_missing_auth_method_is_reported_without_values(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_auth_vars(monkeypatch)
    for name, value in VALID_ENV.items():
        if name != "SNOWFLAKE_PASSWORD":
            monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match="SNOWFLAKE_PASSWORD") as exc_info:
        SnowflakeConfig.from_environment()
    assert "not-a-real-secret" not in str(exc_info.value)


def test_both_auth_methods_set_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_auth_vars(monkeypatch)
    for name, value in VALID_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("SNOWFLAKE_PRIVATE_KEY", "not-a-real-private-key")
    with pytest.raises(ValueError, match="Exactly one") as exc_info:
        SnowflakeConfig.from_environment()
    assert "not-a-real-secret" not in str(exc_info.value)
    assert "not-a-real-private-key" not in str(exc_info.value)


def test_account_url_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_auth_vars(monkeypatch)
    for name, value in VALID_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "example.snowflakecomputing.com")
    with pytest.raises(ValueError, match="account identifier"):
        SnowflakeConfig.from_environment().validate()
