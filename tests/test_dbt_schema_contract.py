from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DBT_PROJECT = PROJECT_ROOT / "dbt" / "pharma_retail" / "dbt_project.yml"
SCHEMA_MACRO = (
    PROJECT_ROOT
    / "dbt"
    / "pharma_retail"
    / "macros"
    / "get_custom_schema.sql"
)


def test_dbt_relations_use_only_precreated_schemas() -> None:
    config = yaml.safe_load(DBT_PROJECT.read_text(encoding="utf-8"))
    project_models = config["models"]["pharma_retail"]

    assert project_models["staging"]["+schema"] == "STAGING"
    assert project_models["intermediate"]["+schema"] == "INTERMEDIATE"
    assert project_models["marts"]["+schema"] == "MARTS"
    assert config["tests"]["pharma_retail"]["+schema"] == "STAGING"


def test_generate_schema_name_does_not_add_target_prefixes() -> None:
    macro = SCHEMA_MACRO.read_text(encoding="utf-8")

    assert "custom_schema_name | trim" in macro
    assert "target.schema ~" not in macro
    assert "target.schema +" not in macro
