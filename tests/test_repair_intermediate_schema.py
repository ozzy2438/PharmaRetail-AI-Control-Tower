from __future__ import annotations

from scripts.repair_intermediate_schema import (
    MODEL_SCHEMAS,
    STAGING_VIEW_MODELS,
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


def test_verify_foundation_checks_database_raw_staging_and_schemas() -> None:
    cursor = FakeCursor(
        {
            "SHOW DATABASES": (["NAME"], [("PHARMARETAIL",)]),
            "SHOW TABLES IN SCHEMA PHARMARETAIL.RAW": (["NAME"], [("UCI_SALES",)]),
            "SHOW TABLES IN SCHEMA PHARMARETAIL.STAGING": (["NAME"], []),
            "SHOW VIEWS IN SCHEMA PHARMARETAIL.STAGING": (
                ["NAME"],
                [(view_name,) for view_name in STAGING_VIEW_MODELS],
            ),
            "SHOW SCHEMAS IN DATABASE PHARMARETAIL": (
                ["NAME"],
                [("RAW",), ("STAGING",), ("INTERMEDIATE",)],
            ),
        }
    )

    schema_names, staging_view_names = verify_foundation(cursor)

    assert cursor.calls == [
        "SHOW DATABASES",
        "SHOW TABLES IN SCHEMA PHARMARETAIL.RAW",
        "SHOW TABLES IN SCHEMA PHARMARETAIL.STAGING",
        "SHOW VIEWS IN SCHEMA PHARMARETAIL.STAGING",
        "SHOW SCHEMAS IN DATABASE PHARMARETAIL",
    ]
    assert schema_names == {"RAW", "STAGING", "INTERMEDIATE"}
    assert staging_view_names == set(STAGING_VIEW_MODELS)


def test_apply_grants_never_grants_create_schema() -> None:
    cursor = FakeCursor({})

    apply_grants(cursor)

    assert cursor.calls[0] == (
        "GRANT USAGE ON DATABASE PHARMARETAIL TO ROLE PHARMARETAIL_DBT"
    )
    for schema in MODEL_SCHEMAS:
        assert (
            f"CREATE SCHEMA IF NOT EXISTS PHARMARETAIL.{schema} WITH MANAGED ACCESS"
            in cursor.calls
        )
        assert (
            f"GRANT USAGE ON SCHEMA PHARMARETAIL.{schema} TO ROLE PHARMARETAIL_DBT"
            in cursor.calls
        )
        assert (
            f"GRANT CREATE VIEW ON SCHEMA PHARMARETAIL.{schema} TO ROLE PHARMARETAIL_DBT"
            in cursor.calls
        )
        assert (
            f"GRANT CREATE TABLE ON SCHEMA PHARMARETAIL.{schema} TO ROLE PHARMARETAIL_DBT"
            in cursor.calls
        )
    for view_name in STAGING_VIEW_MODELS:
        assert (
            "GRANT OWNERSHIP ON VIEW "
            f"PHARMARETAIL.STAGING.{view_name} TO ROLE PHARMARETAIL_DBT "
            "COPY CURRENT GRANTS"
            in cursor.calls
        )
    assert (
        "GRANT OWNERSHIP ON SCHEMA PHARMARETAIL.MARTS "
        "TO ROLE PHARMARETAIL_ADMIN COPY CURRENT GRANTS"
        in cursor.calls
    )
    assert not any("GRANT CREATE SCHEMA" in call for call in cursor.calls)
    assert not any(
        "OWNERSHIP ON SCHEMA" in call and "TO ROLE PHARMARETAIL_DBT" in call
        for call in cursor.calls
    )
    assert not any("OWNERSHIP ON DATABASE" in call for call in cursor.calls)


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
                    ("CREATE VIEW", "SCHEMA", "STAGING"),
                    ("CREATE TABLE", "SCHEMA", "STAGING"),
                    ("USAGE", "SCHEMA", "MARTS"),
                    ("CREATE VIEW", "SCHEMA", "MARTS"),
                    ("CREATE TABLE", "SCHEMA", "MARTS"),
                    *(
                        ("OWNERSHIP", "VIEW", view_name)
                        for view_name in STAGING_VIEW_MODELS
                    ),
                ],
            ),
            "SHOW GRANTS ON SCHEMA PHARMARETAIL.MARTS": (
                ["PRIVILEGE", "GRANTEE_NAME"],
                [("OWNERSHIP", "PHARMARETAIL_ADMIN")],
            ),
        }
    )

    verify_grants(cursor)
    assert cursor.calls[-1] == "SHOW GRANTS ON SCHEMA PHARMARETAIL.MARTS"
