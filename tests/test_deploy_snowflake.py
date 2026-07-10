from __future__ import annotations

from pathlib import Path

import pytest

from scripts.deploy_snowflake import discover_scripts, validate_scripts


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
