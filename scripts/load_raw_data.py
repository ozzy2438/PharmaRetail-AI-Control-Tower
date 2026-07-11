"""Contract-driven, idempotent loader for processed datasets into Snowflake RAW.

Truncate-and-reload per dataset: re-running produces the same end state. Every
attempt (success or failure) is recorded in RAW.LOAD_AUDIT. No dataset is
downloaded or generated here; only the existing processed/quarantine files
under data/ are loaded, per their contracts/*.yml definition.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

from scripts.deploy_snowflake import load_private_key_der
from scripts.validate_snowflake_config import SnowflakeConfig

STAGE = "RAW.RAW_LOAD_STAGE"

# Contract path -> target RAW table. Order matches load-then-report order.
DATASET_TABLES = {
    "contracts/uci_sales.yml": "RAW.UCI_SALES",
    "contracts/uci_returns.yml": "RAW.UCI_RETURNS",
    "contracts/uci_invalid_price.yml": "RAW.UCI_SALES_QUARANTINE",
    "contracts/dim_store.yml": "RAW.DIM_STORE_SEED",
    "contracts/dim_product.yml": "RAW.DIM_PRODUCT_SEED",
}

CONTRACT_TYPE_TO_SNOWFLAKE = {
    "string": "STRING",
    "integer": "NUMBER",
    "number": "FLOAT",
    "timestamp": "TIMESTAMP_NTZ",
    "boolean": "BOOLEAN",
}


@dataclass(frozen=True)
class ContractColumn:
    name: str
    type: str


@dataclass(frozen=True)
class Contract:
    dataset: str
    path: Path
    format: str
    columns: list[ContractColumn]


def load_contract(path: Path) -> Contract:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    columns = [ContractColumn(name=c["name"], type=c["type"]) for c in raw["columns"]]
    return Contract(
        dataset=raw["dataset"], path=Path(raw["path"]), format=raw["format"], columns=columns
    )


@dataclass(frozen=True)
class FileStats:
    row_count: int
    null_counts: dict[str, int]
    duplicate_row_count: int
    sha256: str


def compute_file_stats(contract: Contract) -> FileStats:
    if contract.format == "parquet":
        frame = pd.read_parquet(contract.path)
        missing = [column.name for column in contract.columns if column.name not in frame.columns]
        if missing:
            raise ValueError(f"{contract.path}: missing contract columns in file: {missing}")
    elif contract.format == "csv":
        frame = pd.read_csv(contract.path, dtype=str)
        expected_order = [column.name for column in contract.columns]
        if list(frame.columns) != expected_order:
            raise ValueError(
                f"{contract.path}: CSV column order {list(frame.columns)} does not match "
                f"contract column order {expected_order}"
            )
    else:
        raise ValueError(f"Unsupported contract format: {contract.format}")

    # Every contract column is now guaranteed present (checked above per format).
    null_counts = {
        column.name: int(frame[column.name].isna().sum()) for column in contract.columns
    }
    return FileStats(
        row_count=len(frame),
        null_counts=null_counts,
        duplicate_row_count=int(frame.duplicated().sum()),
        sha256=hashlib.sha256(contract.path.read_bytes()).hexdigest(),
    )


@dataclass
class LoadResult:
    dataset: str
    table: str
    source_file: str
    stats: FileStats
    load_id: str
    loaded_row_count: int | None = None
    status: str = "PENDING"
    error_message: str | None = None

    @property
    def row_count_match(self) -> bool | None:
        if self.loaded_row_count is None:
            return None
        return self.loaded_row_count == self.stats.row_count


def _parquet_column_expression(column: ContractColumn) -> str:
    """Build the SELECT expression for one column when reading Parquet via $1.

    Parquet's native TIMESTAMP columns lose their logical type annotation
    when accessed through Snowflake's semi-structured $1:field syntax: the
    value comes back as the raw physical INT64 (nanoseconds since epoch, the
    pandas/pyarrow default), and a plain ::TIMESTAMP_NTZ cast on that number
    is interpreted as *seconds* since epoch, producing nonsense dates many
    million years off. TO_TIMESTAMP_NTZ(..., 9) tells Snowflake the input is
    nanosecond-scale, which correctly recovers the original value. Every
    other type extracts fine with a direct cast.
    """
    name = column.name
    if column.type == "timestamp":
        return f"to_timestamp_ntz($1:{name}::number, 9) AS {name.upper()}"
    snowflake_type = CONTRACT_TYPE_TO_SNOWFLAKE[column.type]
    return f"$1:{name}::{snowflake_type} AS {name.upper()}"


def build_copy_sql(
    contract: Contract, table: str, stage_file: str, load_id: str, source_file: str
) -> str:
    """Build a single COPY INTO that populates source + audit columns atomically.

    Audit columns are set inline (not via a follow-up UPDATE) because they are
    declared NOT NULL, and a separate UPDATE-after-COPY would violate that
    constraint the instant COPY inserts the row.

    stage_file is the bare filename on the internal stage (used to locate the
    file); source_file is the contract's declared path (e.g.
    data/processed/uci_sales_clean.parquet), stored in _SOURCE_FILE so landed
    rows match RAW.LOAD_AUDIT.SOURCE_FILE and are self-describing.
    """
    if contract.format == "parquet":
        select_parts = [_parquet_column_expression(column) for column in contract.columns]
        file_format = "(TYPE = PARQUET)"
    elif contract.format == "csv":
        select_parts = [
            f"${index}::{CONTRACT_TYPE_TO_SNOWFLAKE[column.type]} AS {column.name.upper()}"
            for index, column in enumerate(contract.columns, start=1)
        ]
        file_format = (
            "(TYPE = CSV SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '\"' NULL_IF = (''))"
        )
    else:
        raise ValueError(f"Unsupported contract format: {contract.format}")

    if "'" in load_id or "'" in stage_file or "'" in source_file:
        raise ValueError("load_id/stage_file/source_file must not contain a single quote")

    select_parts.append(f"'{load_id}' AS _LOAD_ID")
    select_parts.append("CURRENT_TIMESTAMP() AS _LOADED_AT")
    select_parts.append(f"'{source_file}' AS _SOURCE_FILE")

    column_list = ", ".join(column.name.upper() for column in contract.columns)
    column_list += ", _LOAD_ID, _LOADED_AT, _SOURCE_FILE"
    select_clause = ",\n        ".join(select_parts)

    return (
        f"COPY INTO {table} ({column_list})\n"
        f"FROM (\n"
        f"    SELECT\n"
        f"        {select_clause}\n"
        f"    FROM @{STAGE}/{stage_file}\n"
        f")\n"
        f"FILE_FORMAT = {file_format}\n"
        f"PURGE = FALSE"
    )


def connect(config: SnowflakeConfig):
    """Open a Snowflake connection for the RAW load.

    Duplicates deploy_snowflake.execute_scripts' small auth-branching (rather
    than importing it) to avoid modifying the already-verified Phase 1
    deployment path; the actual key-conversion logic is reused, not repeated.
    """
    import snowflake.connector

    connect_kwargs: dict[str, object] = {
        "account": config.account,
        "user": config.user,
        "role": config.role,
        "warehouse": config.warehouse,
        "database": config.database,
        "session_parameters": {"QUERY_TAG": "PHARMARETAIL_RAW_INGESTION_LOAD"},
    }
    if config.auth_method == "key_pair":
        connect_kwargs["private_key"] = load_private_key_der(
            config.private_key_pem, config.private_key_passphrase
        )
    else:
        connect_kwargs["password"] = config.password
    return snowflake.connector.connect(**connect_kwargs)


def write_audit_row(
    cursor, result: LoadResult, started_at: datetime, completed_at: datetime
) -> None:
    cursor.execute(
        "INSERT INTO RAW.LOAD_AUDIT ("
        "LOAD_ID, TABLE_NAME, SOURCE_FILE, FILE_SHA256, SOURCE_ROW_COUNT, "
        "LOADED_ROW_COUNT, ROW_COUNT_MATCH, NULL_COUNTS, DUPLICATE_ROW_COUNT, "
        "LOAD_STATUS, ERROR_MESSAGE, STARTED_AT, COMPLETED_AT"
        ") SELECT %(load_id)s, %(table_name)s, %(source_file)s, %(file_sha256)s, "
        "%(source_row_count)s, %(loaded_row_count)s, %(row_count_match)s, "
        "PARSE_JSON(%(null_counts)s), %(duplicate_row_count)s, %(load_status)s, "
        "%(error_message)s, %(started_at)s, %(completed_at)s",
        {
            "load_id": result.load_id,
            "table_name": result.table,
            "source_file": result.source_file,
            "file_sha256": result.stats.sha256,
            "source_row_count": result.stats.row_count,
            "loaded_row_count": result.loaded_row_count,
            "row_count_match": result.row_count_match,
            "null_counts": json.dumps(result.stats.null_counts),
            "duplicate_row_count": result.stats.duplicate_row_count,
            "load_status": result.status,
            "error_message": result.error_message,
            "started_at": started_at,
            "completed_at": completed_at,
        },
    )


def load_dataset(cursor, contract_path: Path, table: str) -> LoadResult:
    """Load one dataset. Never raises: a failure is recorded as a FAILED
    LoadResult (with its own RAW.LOAD_AUDIT row) so the caller can continue
    attempting the remaining datasets and still produce a complete
    reconciliation report covering every dataset, not just the ones that
    happened to run before the first failure.
    """
    contract = load_contract(contract_path)
    stats = compute_file_stats(contract)
    load_id = uuid.uuid4().hex
    result = LoadResult(
        dataset=contract.dataset,
        table=table,
        source_file=str(contract.path),
        stats=stats,
        load_id=load_id,
    )
    started_at = datetime.now(timezone.utc)
    try:
        stage_file = contract.path.resolve().name
        cursor.execute(
            f"PUT 'file://{contract.path.resolve().as_posix()}' @{STAGE} "
            "AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
        )
        cursor.execute(f"TRUNCATE TABLE {table}")
        cursor.execute(build_copy_sql(contract, table, stage_file, load_id, result.source_file))
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        (loaded_row_count,) = cursor.fetchone()
        result.loaded_row_count = int(loaded_row_count)
        cursor.execute(f"REMOVE @{STAGE}/{stage_file}")
        result.status = "SUCCESS" if result.row_count_match else "ROW_COUNT_MISMATCH"
    except Exception as exc:
        result.status = "FAILED"
        result.error_message = str(exc)[:2000]
    finally:
        write_audit_row(cursor, result, started_at, datetime.now(timezone.utc))
    return result


def generate_reconciliation_report(results: list[LoadResult]) -> str:
    lines = [
        "# Data load reconciliation report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "| Dataset | Table | Source rows | Loaded rows | Match | Duplicates | "
        "Null columns (non-zero) | SHA-256 | Status |",
        "|---|---|---:|---:|---|---:|---|---|---|",
    ]
    for result in results:
        nulls = ", ".join(f"{k}={v}" for k, v in result.stats.null_counts.items() if v) or "none"
        if result.row_count_match is None:
            match = "n/a"
        else:
            match = "yes" if result.row_count_match else "no"
        loaded_rows = result.loaded_row_count if result.loaded_row_count is not None else "n/a"
        lines.append(
            f"| {result.dataset} | {result.table} | {result.stats.row_count} | "
            f"{loaded_rows} | {match} | {result.stats.duplicate_row_count} | "
            f"{nulls} | `{result.stats.sha256[:12]}…` | {result.status} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report-path", type=Path, default=Path("docs/data_load_reconciliation.md")
    )
    args = parser.parse_args()

    config = SnowflakeConfig.from_environment()
    config.validate()
    connection = connect(config)
    results: list[LoadResult] = []
    try:
        cursor = connection.cursor()
        for contract_path_str, table in DATASET_TABLES.items():
            print(f"Loading {table} from {contract_path_str}")
            result = load_dataset(cursor, Path(contract_path_str), table)
            results.append(result)
            print(
                f"  source_rows={result.stats.row_count} loaded_rows={result.loaded_row_count} "
                f"match={result.row_count_match} duplicates={result.stats.duplicate_row_count} "
                f"status={result.status}"
            )
    finally:
        connection.close()

    report = generate_reconciliation_report(results)
    args.report_path.write_text(report, encoding="utf-8")
    print(f"Reconciliation report written to {args.report_path}")

    unhealthy = [result for result in results if result.status != "SUCCESS"]
    if unhealthy:
        names = ", ".join(f"{result.table}({result.status})" for result in unhealthy)
        print(f"One or more datasets did not load cleanly: {names}")
        print("Review RAW.LOAD_AUDIT and the reconciliation report.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
