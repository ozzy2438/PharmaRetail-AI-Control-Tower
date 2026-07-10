from __future__ import annotations

from pathlib import Path

import pytest

from scripts.deploy_snowflake import discover_scripts, execute_scripts, validate_scripts
from scripts.validate_snowflake_config import SnowflakeConfig


def test_scripts_are_discovered_in_order(tmp_path: Path) -> None:
    (tmp_path / "02_second.sql").write_text("SELECT 2;", encoding="utf-8")
    (tmp_path / "01_first.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "rollback.sql").write_text("SELECT 0;", encoding="utf-8")
    assert [path.name for path in discover_scripts(tmp_path)] == [
        "01_first.sql",
        "02_second.sql",
    ]


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
