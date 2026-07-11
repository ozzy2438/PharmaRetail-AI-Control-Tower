from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from scripts.load_raw_data import (
    Contract,
    ContractColumn,
    FileStats,
    LoadResult,
    build_copy_sql,
    compute_file_stats,
    connect,
    generate_reconciliation_report,
    load_contract,
    load_dataset,
)
from scripts.validate_snowflake_config import SnowflakeConfig


def _write_parquet_contract(tmp_path: Path) -> Path:
    data_path = tmp_path / "fixture_sales.parquet"
    frame = pd.DataFrame(
        {
            "invoice": ["INV1", "INV2", "INV3", "INV4", "INV5"],
            "stock_code": ["A", "B", "C", "D", "E"],
            "description": ["d1", None, "d3", "d4", "d5"],
            "quantity": [1, 2, 3, 4, 5],
            "invoice_date": pd.to_datetime(["2020-01-01"] * 5),
            "price": [1.0, 2.0, 3.0, 4.0, 5.0],
            "customer_id": ["C1", None, "C3", "C4", "C5"],
            "country": ["AU"] * 5,
            "is_customer_identified": [True, False, True, True, True],
        }
    )
    frame.to_parquet(data_path)
    contract_yaml = {
        "version": 1,
        "dataset": "fixture_sales",
        "path": str(data_path),
        "format": "parquet",
        "columns": [
            {"name": "invoice", "type": "string", "nullable": False},
            {"name": "stock_code", "type": "string", "nullable": False},
            {"name": "description", "type": "string", "nullable": True},
            {"name": "quantity", "type": "integer", "nullable": False},
            {"name": "invoice_date", "type": "timestamp", "nullable": False},
            {"name": "price", "type": "number", "nullable": False},
            {"name": "customer_id", "type": "string", "nullable": True},
            {"name": "country", "type": "string", "nullable": False},
            {"name": "is_customer_identified", "type": "boolean", "nullable": False},
        ],
    }
    contract_path = tmp_path / "fixture_sales.yml"
    contract_path.write_text(yaml.dump(contract_yaml), encoding="utf-8")
    return contract_path


def _write_csv_contract(tmp_path: Path) -> Path:
    data_path = tmp_path / "fixture_stores.csv"
    frame = pd.DataFrame(
        {
            "store_id": ["S1", "S2", "S3"],
            "postcode": ["1000", None, "3000"],
        }
    )
    frame.to_csv(data_path, index=False)
    contract_yaml = {
        "version": 1,
        "dataset": "fixture_stores",
        "path": str(data_path),
        "format": "csv",
        "columns": [
            {"name": "store_id", "type": "string", "nullable": False},
            {"name": "postcode", "type": "string", "nullable": True},
        ],
    }
    contract_path = tmp_path / "fixture_stores.yml"
    contract_path.write_text(yaml.dump(contract_yaml), encoding="utf-8")
    return contract_path


def test_load_contract_parses_columns(tmp_path: Path) -> None:
    contract_path = _write_parquet_contract(tmp_path)
    contract = load_contract(contract_path)
    assert contract.dataset == "fixture_sales"
    assert contract.format == "parquet"
    assert [c.name for c in contract.columns][:3] == ["invoice", "stock_code", "description"]


def test_compute_file_stats_parquet(tmp_path: Path) -> None:
    contract = load_contract(_write_parquet_contract(tmp_path))
    stats = compute_file_stats(contract)
    assert stats.row_count == 5
    assert stats.null_counts["description"] == 1
    assert stats.null_counts["customer_id"] == 1
    assert stats.null_counts["invoice"] == 0
    assert stats.duplicate_row_count == 0
    assert len(stats.sha256) == 64


def test_compute_file_stats_csv(tmp_path: Path) -> None:
    contract = load_contract(_write_csv_contract(tmp_path))
    stats = compute_file_stats(contract)
    assert stats.row_count == 3
    assert stats.null_counts["postcode"] == 1


def test_compute_file_stats_detects_duplicates(tmp_path: Path) -> None:
    contract_path = _write_parquet_contract(tmp_path)
    contract = load_contract(contract_path)
    frame = pd.read_parquet(contract.path)
    frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    frame.to_parquet(contract.path)
    stats = compute_file_stats(contract)
    assert stats.duplicate_row_count == 1
    assert stats.row_count == 6


def test_compute_file_stats_rejects_csv_column_order_mismatch(tmp_path: Path) -> None:
    contract_path = _write_csv_contract(tmp_path)
    contract = load_contract(contract_path)
    reordered = Contract(
        dataset=contract.dataset,
        path=contract.path,
        format=contract.format,
        columns=list(reversed(contract.columns)),
    )
    with pytest.raises(ValueError, match="column order"):
        compute_file_stats(reordered)


def test_compute_file_stats_rejects_missing_parquet_column(tmp_path: Path) -> None:
    contract_path = _write_parquet_contract(tmp_path)
    contract = load_contract(contract_path)
    drifted = Contract(
        dataset=contract.dataset,
        path=contract.path,
        format=contract.format,
        columns=[*contract.columns, ContractColumn(name="not_in_file", type="string")],
    )
    with pytest.raises(ValueError, match="missing contract columns"):
        compute_file_stats(drifted)


def test_build_copy_sql_parquet_uses_named_field_access(tmp_path: Path) -> None:
    contract = load_contract(_write_parquet_contract(tmp_path))
    sql = build_copy_sql(
        contract,
        "RAW.FIXTURE_SALES",
        "fixture_sales.parquet",
        "load-123",
        "data/processed/fixture_sales.parquet",
    )
    assert "$1:invoice::STRING AS INVOICE" in sql
    assert "'load-123' AS _LOAD_ID" in sql
    assert "FROM @RAW.RAW_LOAD_STAGE/fixture_sales.parquet" in sql
    assert "'data/processed/fixture_sales.parquet' AS _SOURCE_FILE" in sql
    assert "FILE_FORMAT = (TYPE = PARQUET)" in sql
    # Parquet TIMESTAMP columns lose their logical type through $1:field
    # access (Snowflake gotcha) and must go through TO_TIMESTAMP_NTZ(..., 9),
    # not a plain ::TIMESTAMP_NTZ cast, or dates come back off by ~1e9.
    assert "to_timestamp_ntz($1:invoice_date::number, 9) AS INVOICE_DATE" in sql
    assert "$1:invoice_date::TIMESTAMP_NTZ" not in sql


def test_build_copy_sql_csv_uses_positional_access(tmp_path: Path) -> None:
    contract = load_contract(_write_csv_contract(tmp_path))
    sql = build_copy_sql(
        contract,
        "RAW.FIXTURE_STORES",
        "fixture_stores.csv",
        "load-456",
        "data/processed/fixture_stores.csv",
    )
    assert "$1::STRING AS STORE_ID" in sql
    assert "$2::STRING AS POSTCODE" in sql
    assert "TYPE = CSV" in sql


def test_build_copy_sql_rejects_quote_in_load_id(tmp_path: Path) -> None:
    contract = load_contract(_write_parquet_contract(tmp_path))
    with pytest.raises(ValueError, match="single quote"):
        build_copy_sql(
            contract, "RAW.FIXTURE_SALES", "fixture_sales.parquet", "bad'id", "source.parquet"
        )


def test_build_copy_sql_rejects_quote_in_source_file(tmp_path: Path) -> None:
    contract = load_contract(_write_parquet_contract(tmp_path))
    with pytest.raises(ValueError, match="single quote"):
        build_copy_sql(
            contract, "RAW.FIXTURE_SALES", "fixture_sales.parquet", "load-1", "bad'source.parquet"
        )


def test_load_result_row_count_match() -> None:
    stats = FileStats(row_count=5, null_counts={}, duplicate_row_count=0, sha256="x")
    result = LoadResult(dataset="d", table="t", source_file="f", stats=stats, load_id="l")
    assert result.row_count_match is None
    result.loaded_row_count = 5
    assert result.row_count_match is True
    result.loaded_row_count = 4
    assert result.row_count_match is False


class FakeCursor:
    def __init__(self, count_value: int) -> None:
        self.executed: list[tuple[str, object]] = []
        self._count_value = count_value

    def execute(self, sql: str, params: object = None) -> "FakeCursor":
        self.executed.append((sql, params))
        return self

    def fetchone(self) -> tuple[int]:
        return (self._count_value,)


def test_load_dataset_success_records_audit(tmp_path: Path) -> None:
    contract_path = _write_parquet_contract(tmp_path)
    cursor = FakeCursor(count_value=5)
    result = load_dataset(cursor, contract_path, "RAW.FIXTURE_SALES")
    assert result.status == "SUCCESS"
    assert result.row_count_match is True
    kinds = [sql.split()[0] for sql, _ in cursor.executed]
    assert kinds == ["PUT", "TRUNCATE", "COPY", "SELECT", "REMOVE", "INSERT"]
    insert_sql, insert_params = cursor.executed[-1]
    assert insert_params["load_status"] == "SUCCESS"
    assert insert_params["source_row_count"] == 5
    assert insert_params["loaded_row_count"] == 5


def test_load_dataset_row_count_mismatch_is_recorded(tmp_path: Path) -> None:
    contract_path = _write_parquet_contract(tmp_path)
    cursor = FakeCursor(count_value=4)
    result = load_dataset(cursor, contract_path, "RAW.FIXTURE_SALES")
    assert result.status == "ROW_COUNT_MISMATCH"
    assert result.row_count_match is False


def test_load_dataset_failure_returns_failed_result_without_raising(tmp_path: Path) -> None:
    # load_dataset must not raise: the caller (main's loop) needs every
    # dataset attempted and audited even if an earlier one failed, so the
    # reconciliation report always covers the whole batch.
    contract_path = _write_parquet_contract(tmp_path)

    class FailingCursor(FakeCursor):
        def execute(self, sql: str, params: object = None) -> "FailingCursor":
            self.executed.append((sql, params))
            if sql.startswith("COPY"):
                raise RuntimeError("simulated COPY failure")
            return self

    cursor = FailingCursor(count_value=5)
    result = load_dataset(cursor, contract_path, "RAW.FIXTURE_SALES")

    assert result.status == "FAILED"
    assert result.loaded_row_count is None
    assert result.row_count_match is None
    assert "simulated COPY failure" in result.error_message

    insert_calls = [(sql, params) for sql, params in cursor.executed if sql.startswith("INSERT")]
    assert len(insert_calls) == 1
    _, insert_params = insert_calls[0]
    assert insert_params["load_status"] == "FAILED"
    assert "simulated COPY failure" in insert_params["error_message"]
    assert insert_params["loaded_row_count"] is None


def test_generate_reconciliation_report_marks_mismatch() -> None:
    stats = FileStats(row_count=10, null_counts={"a": 2}, duplicate_row_count=0, sha256="abc123")
    ok = LoadResult(
        dataset="ok_dataset", table="RAW.OK", source_file="f1", stats=stats, load_id="l1"
    )
    ok.loaded_row_count = 10
    ok.status = "SUCCESS"
    bad = LoadResult(
        dataset="bad_dataset", table="RAW.BAD", source_file="f2", stats=stats, load_id="l2"
    )
    bad.loaded_row_count = 9
    bad.status = "ROW_COUNT_MISMATCH"

    report = generate_reconciliation_report([ok, bad])
    assert "ok_dataset" in report
    assert "| yes |" in report
    assert "bad_dataset" in report
    assert "| no |" in report
    assert "a=2" in report


def test_generate_reconciliation_report_renders_na_for_failed_dataset() -> None:
    stats = FileStats(row_count=10, null_counts={}, duplicate_row_count=0, sha256="abc123")
    failed = LoadResult(
        dataset="failed_dataset", table="RAW.FAILED", source_file="f3", stats=stats, load_id="l3"
    )
    failed.status = "FAILED"
    failed.error_message = "boom"

    report = generate_reconciliation_report([failed])
    assert failed.row_count_match is None
    assert "| n/a |" in report
    assert "None" not in report


def test_connect_uses_key_pair_and_sets_warehouse_database(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_connect(**kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("snowflake.connector.connect", fake_connect)
    config = SnowflakeConfig(
        account="ORG-ACCOUNT",
        user="SVC_PHARMARETAIL_CICD",
        role="PHARMARETAIL_ADMIN",
        warehouse="WH_PHARMARETAIL",
        database="PHARMARETAIL_AI_CONTROL_TOWER",
        private_key_pem=_generate_test_private_key_pem(),
    )
    connect(config)
    assert captured["warehouse"] == "WH_PHARMARETAIL"
    assert captured["database"] == "PHARMARETAIL_AI_CONTROL_TOWER"
    assert "private_key" in captured
    assert "password" not in captured


def _generate_test_private_key_pem() -> str:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem.decode("utf-8")
