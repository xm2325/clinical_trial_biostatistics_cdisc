import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.traceability import validate_traceability


REGISTRY_COLUMNS = [
    "tlf_id",
    "title",
    "objective",
    "population",
    "endpoint",
    "method",
    "source_domains",
    "analysis_dataset",
    "output_file",
    "qc_evidence",
]


def _write_fixture(root: Path, required_columns=None):
    required_columns = required_columns or ["TRT01A", "Statistic", "Value"]
    (root / "spec").mkdir()
    (root / "outputs").mkdir()

    registry = pd.DataFrame(
        [[
            "T01",
            "Demographics",
            "Describe baseline",
            "Safety population",
            "Age sex race",
            "Descriptive statistics",
            "DM|EX",
            "outputs/adsl_style.csv",
            "outputs/table1_demographics.csv",
            "outputs/qc_report.csv",
        ]],
        columns=REGISTRY_COLUMNS,
    )
    registry.to_csv(root / "spec" / "analysis_traceability.csv", index=False)
    (root / "spec" / "output_contracts.json").write_text(
        json.dumps(
            {
                "T01": {
                    "output_file": "outputs/table1_demographics.csv",
                    "required_columns": required_columns,
                    "min_rows": 1,
                }
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame([{"USUBJID": "01"}]).to_csv(root / "outputs" / "adsl_style.csv", index=False)
    pd.DataFrame([{"check": "x", "passed": True}]).to_csv(root / "outputs" / "qc_report.csv", index=False)
    pd.DataFrame([{"TRT01A": "Placebo", "Statistic": "N", "Value": "1"}]).to_csv(
        root / "outputs" / "table1_demographics.csv", index=False
    )


def test_traceability_passes_complete_output_contract(tmp_path):
    _write_fixture(tmp_path)
    detail, metrics = validate_traceability(tmp_path)
    assert metrics["planned_tlfs"] == 1
    assert metrics["passed_tlfs"] == 1
    assert metrics["all_passed"] is True
    assert detail.iloc[0]["required_columns_ok"]
    assert len(detail.iloc[0]["output_sha256"]) == 64


def test_traceability_reports_missing_required_output_column(tmp_path):
    _write_fixture(tmp_path, required_columns=["TRT01A", "Statistic", "Value", "MissingColumn"])
    detail, metrics = validate_traceability(tmp_path)
    assert metrics["all_passed"] is False
    assert detail.iloc[0]["required_columns_ok"] is False or not bool(detail.iloc[0]["required_columns_ok"])
    assert "MissingColumn" in detail.iloc[0]["missing_columns"]


def test_traceability_rejects_registry_contract_id_mismatch(tmp_path):
    _write_fixture(tmp_path)
    contracts_path = tmp_path / "spec" / "output_contracts.json"
    contracts_path.write_text(json.dumps({"T99": {"output_file": "x", "required_columns": [], "min_rows": 1}}), encoding="utf-8")
    with pytest.raises(ValueError, match="Registry/contract ID mismatch"):
        validate_traceability(tmp_path)
