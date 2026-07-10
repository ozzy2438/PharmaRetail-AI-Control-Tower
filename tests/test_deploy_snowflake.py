from __future__ import annotations

from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from scripts.deploy_snowflake import (
    discover_scripts,
    execute_scripts,
    load_private_key_der,
    validate_scripts,
)
from scripts.validate_snowflake_config import SnowflakeConfig


def test_scripts_are_discovered_in_order(tmp_path: Path) -> None:
    (tmp_path / "02_second.sql").write_text("SELECT 2;", encoding="utf-8")
    (tmp_path / "01_first.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "rollback.sql").write_text("SELECT 0;", encoding="utf-8")
    assert [path.name for path in discover_scripts(tmp_path)] == [
        "01_first.sql",
        "02_second.sql",
    ]


def test_explicit_script_order_is_preserved(tmp_path: Path) -> None:
    second = tmp_path / "06_validation.sql"
    first = tmp_path / "04_grants.sql"
    second.write_text("SELECT 2;", encoding="utf-8")
    first.write_text("SELECT 1;", encoding="utf-8")
    scripts = [first, second]
    validate_scripts(scripts)
    assert scripts == [first, second]


def test_empty_script_set_is_rejected() -> None:
    with pytest.raises(ValueError, match="No ordered"):
        validate_scripts([])


def test_execute_scripts_uses_string_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = tmp_path / "01_test.sql"
    script.write_text("SELECT 1;", encoding="utf-8")
    executed: list[str] = []

    class FakeCursor:
        def close(self) -> None:
            return None

    class FakeConnection:
        def execute_string(self, sql: str) -> list[FakeCursor]:
            executed.append(sql)
            return [FakeCursor()]

        def close(self) -> None:
            return None

    monkeypatch.setattr("snowflake.connector.connect", lambda **_: FakeConnection())
    config = SnowflakeConfig(
        account="ORG-ACCOUNT",
        user="CI_USER",
        password="not-a-real-secret",
        role="ACCOUNTADMIN",
        warehouse="WH_PHARMARETAIL",
        database="PHARMARETAIL_AI_CONTROL_TOWER",
    )
    execute_scripts(config, [script])
    assert executed == ["SELECT 1;"]


def _generate_test_private_key_pem(passphrase: str | None) -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    encryption: serialization.KeySerializationEncryption
    if passphrase:
        encryption = serialization.BestAvailableEncryption(passphrase.encode("utf-8"))
    else:
        encryption = serialization.NoEncryption()
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption,
    )
    return pem.decode("utf-8")


def test_load_private_key_der_supports_encrypted_pem() -> None:
    pem_text = _generate_test_private_key_pem(passphrase="correct-horse-battery-staple")
    der = load_private_key_der(pem_text, "correct-horse-battery-staple")
    assert isinstance(der, bytes)
    assert len(der) > 0


def test_execute_scripts_uses_private_key_for_key_pair_auth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = tmp_path / "01_test.sql"
    script.write_text("SELECT 1;", encoding="utf-8")
    captured_kwargs: dict[str, object] = {}

    class FakeCursor:
        def close(self) -> None:
            return None

    class FakeConnection:
        def execute_string(self, sql: str) -> list[FakeCursor]:
            return [FakeCursor()]

        def close(self) -> None:
            return None

    def fake_connect(**kwargs: object) -> FakeConnection:
        captured_kwargs.update(kwargs)
        return FakeConnection()

    monkeypatch.setattr("snowflake.connector.connect", fake_connect)
    config = SnowflakeConfig(
        account="ORG-ACCOUNT",
        user="SVC_PHARMARETAIL_CICD",
        role="PHARMARETAIL_ADMIN",
        warehouse="WH_PHARMARETAIL",
        database="PHARMARETAIL_AI_CONTROL_TOWER",
        private_key_pem=_generate_test_private_key_pem(passphrase=None),
    )
    execute_scripts(config, [script])
    assert "private_key" in captured_kwargs
    assert isinstance(captured_kwargs["private_key"], bytes)
    assert "password" not in captured_kwargs
