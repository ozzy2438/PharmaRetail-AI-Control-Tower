from __future__ import annotations

import pytest
from snowflake.connector.errors import ProgrammingError

from scripts.validate_snowflake_foundation import as_boolean, expect_denied


class DeniedCursor:
    def execute(self, _: str) -> None:
        raise ProgrammingError("access denied")


class AllowedCursor:
    def execute(self, _: str) -> None:
        return None


def test_expected_denial_is_accepted() -> None:
    expect_denied(DeniedCursor(), "SELECT 1")  # type: ignore[arg-type]


def test_unexpected_access_fails_validation() -> None:
    with pytest.raises(AssertionError, match="Expected access denial"):
        expect_denied(AllowedCursor(), "SELECT 1")  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [True, "true", "TRUE", " true "])
def test_snowflake_boolean_normalization(value: object) -> None:
    assert as_boolean(value)
