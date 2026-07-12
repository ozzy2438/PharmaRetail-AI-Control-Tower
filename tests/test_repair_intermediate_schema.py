from __future__ import annotations

from scripts.repair_intermediate_schema import (
    apply_grants,
    verify_foundation,
    verify_grants,
)


class FakeCursor:
    def __init__(self, responses: dict[str, tuple[list[str], list[tuple[object, ...]]]]) -> None:
        self.responses = responses
        self.calls: list[str] = []
        self.description: list[tuple[str]] = []
        self.rows: list[tuple[object, ...]] = []

    def execute(self, statement: str) -> None:
        self.calls.append(statement)
        columns, rows = self.responses.get(statement, ([], []))
        self.description = [(column,) for column in columns]
        self.rows = rows

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows


def test_verify_foundation_checks_database_and_raw_staging_objects() -> None:
    cursor = FakeCursor(
        {
            "SHOW DATABASES": (["NAME"], [("PHARMARETAIL",)]),
            "SHOW TABLES IN SCHEMA PHARMARETAIL.RAW": (["NAME"], [("UCI_SALES",)]),
            "SHOW TABLES IN SCHEMA PHARMARETAIL.STAGING": (["NAME"], []),
            "SHOW VIEWS IN SCHEMA PHARMARETAIL.STAGING": (["NAME"], [("STG_SALES",)]),
        }
    )

    staging_views = verify_foundation(cursor)

    assert cursor.calls == [
        "SHOW DATABASES",
        "SHOW TABLES IN SCHEMA PHARMARETAIL.RAW",
        "SHOW TABLES IN SCHEMA PHARMARETAIL.STAGING",
        "SHOW VIEWS IN SCHEMA PHARMARETAIL.STAGING",
    ]
    assert staging_views == {"STG_SALES"}


def test_apply_grants_never_grants_create_schema() -> None:
    cursor = FakeCursor({})

    apply_grants(cursor)

    assert cursor.calls == [
        "CREATE SCHEMA IF NOT EXISTS PHARMARETAIL.INTERMEDIATE",
        "GRANT USAGE ON DATABASE PHARMARETAIL TO ROLE PHARMARETAIL_DBT",
        "GRANT USAGE ON SCHEMA PHARMARETAIL.INTERMEDIATE TO ROLE PHARMARETAIL_DBT",
        "GRANT CREATE VIEW ON SCHEMA PHARMARETAIL.INTERMEDIATE TO ROLE PHARMARETAIL_DBT",
        "GRANT CREATE TABLE ON SCHEMA PHARMARETAIL.INTERMEDIATE TO ROLE PHARMARETAIL_DBT",
        "GRANT USAGE ON SCHEMA PHARMARETAIL.STAGING TO ROLE PHARMARETAIL_DBT",
        "GRANT SELECT ON ALL VIEWS IN SCHEMA PHARMARETAIL.STAGING TO ROLE PHARMARETAIL_DBT",
    ]
    assert not any("GRANT CREATE SCHEMA" in call for call in cursor.calls)


def test_verify_grants_accepts_qualified_and_unqualified_names() -> None:
    cursor = FakeCursor(
        {
            "SHOW GRANTS TO ROLE PHARMARETAIL_DBT": (
                ["PRIVILEGE", "GRANTED_ON", "NAME"],
                [
                    ("USAGE", "DATABASE", "PHARMARETAIL"),
                    ("USAGE", "SCHEMA", "PHARMARETAIL.INTERMEDIATE"),
                    ("CREATE VIEW", "SCHEMA", "INTERMEDIATE"),
                    ("CREATE TABLE", "SCHEMA", '"PHARMARETAIL"."INTERMEDIATE"'),
                    ("USAGE", "SCHEMA", "STAGING"),
                    ("SELECT", "VIEW", "STG_STORE"),
                ],
            )
        }
    )

    verify_grants(cursor, {"STG_STORE"})
