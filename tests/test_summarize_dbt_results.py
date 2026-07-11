from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.summarize_dbt_results import main, summarize

SAMPLE_RUN_RESULTS = {
    "metadata": {"dbt_version": "1.7.19", "generated_at": "2026-07-11T00:00:00Z"},
    "results": [
        {
            "unique_id": "model.pharma_retail.stg_uci_sales",
            "status": "success",
            "execution_time": 1.234,
        },
        {
            "unique_id": "test.pharma_retail.not_null_stg_uci_sales_invoice_number.abc123",
            "status": "pass",
            "execution_time": 0.5,
        },
        {
            "unique_id": "test.pharma_retail.assert_fct_sales_daily_reconciles_to_staging",
            "status": "fail",
            "execution_time": 0.75,
        },
    ],
}


def test_summarize_includes_all_nodes_and_status_counts() -> None:
    summary = summarize(SAMPLE_RUN_RESULTS)
    assert "stg_uci_sales" in summary
    assert "not_null_stg_uci_sales_invoice_number" in summary
    assert "assert_fct_sales_daily_reconciles_to_staging" in summary
    assert "1 fail" in summary
    assert "1 pass" in summary
    assert "1 success" in summary
    assert "1.7.19" in summary


def test_summarize_handles_no_results() -> None:
    summary = summarize({"metadata": {}, "results": []})
    assert "no results" in summary


def test_main_writes_summary_and_returns_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_results_path = tmp_path / "run_results.json"
    run_results_path.write_text(json.dumps(SAMPLE_RUN_RESULTS), encoding="utf-8")
    output_path = tmp_path / "summary.md"
    argv = [
        "summarize_dbt_results.py",
        "--run-results",
        str(run_results_path),
        "--output",
        str(output_path),
    ]
    monkeypatch.setattr("sys.argv", argv)

    assert main() == 0
    assert "stg_uci_sales" in output_path.read_text(encoding="utf-8")


def test_main_reports_missing_run_results(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing_path = tmp_path / "does_not_exist.json"
    output_path = tmp_path / "summary.md"
    argv = [
        "summarize_dbt_results.py",
        "--run-results",
        str(missing_path),
        "--output",
        str(output_path),
    ]
    monkeypatch.setattr("sys.argv", argv)

    assert main() == 1
    assert "No run_results.json found" in output_path.read_text(encoding="utf-8")
