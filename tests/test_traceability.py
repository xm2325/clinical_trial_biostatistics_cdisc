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
    "registry_version",
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
            "0.14.0",
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
        json.dumps({
            "T01": {
                "output_file": "outputs/table1_demographics.csv",
                "required_columns": required_columns,
                "min_rows": 1,
            }
        }),
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
    assert metrics["analysis_version"] == "0.14.0"
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
    contracts_path.write_text(
        json.dumps({"T99": {"output_file": "x", "required_columns": [], "min_rows": 1}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Registry/contract ID mismatch"):
        validate_traceability(tmp_path)


def test_traceability_rejects_mixed_registry_versions(tmp_path):
    _write_fixture(tmp_path)
    path = tmp_path / "spec" / "analysis_traceability.csv"
    registry = pd.read_csv(path, dtype=str)
    second = registry.copy()
    second.loc[0, "tlf_id"] = "T02"
    second.loc[0, "registry_version"] = "0.13.0"
    second.loc[0, "output_file"] = "outputs/table2.csv"
    registry = pd.concat([registry, second], ignore_index=True)
    registry.to_csv(path, index=False)
    contracts = json.loads((tmp_path / "spec" / "output_contracts.json").read_text(encoding="utf-8"))
    contracts["T02"] = {"output_file": "outputs/table2.csv", "required_columns": [], "min_rows": 1}
    (tmp_path / "spec" / "output_contracts.json").write_text(json.dumps(contracts), encoding="utf-8")
    with pytest.raises(ValueError, match="one non-empty registry_version"):
        validate_traceability(tmp_path)


def test_repository_registry_is_v016_with_23_controlled_tlfs():
    registry = pd.read_csv(ROOT / "spec" / "analysis_traceability.csv", dtype=str).fillna("")
    contracts = json.loads((ROOT / "spec" / "output_contracts.json").read_text(encoding="utf-8"))

    assert set(registry["registry_version"]) == {"0.16.0"}
    assert registry["tlf_id"].tolist() == [f"T{i:02d}" for i in range(1, 24)]
    assert set(registry["tlf_id"]) == set(contracts)


def test_repository_t12_requires_cross_package_qc_but_t23_does_not_overclaim_it():
    registry = pd.read_csv(ROOT / "spec" / "analysis_traceability.csv", dtype=str).fillna("")
    t12 = registry.loc[registry["tlf_id"] == "T12"].iloc[0]
    t23 = registry.loc[registry["tlf_id"] == "T23"].iloc[0]

    assert "outputs/mmrm_cross_package_qc.csv" in t12["qc_evidence"].split("|")
    assert "outputs/mmrm_cross_package_qc.csv" not in t23["qc_evidence"].split("|")
    assert "outputs/multiplicity_qc.csv" in t23["qc_evidence"].split("|")
