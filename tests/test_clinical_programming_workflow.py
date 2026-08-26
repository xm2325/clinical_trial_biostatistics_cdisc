from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from cdisc_portfolio.clinical_programming_workflow import (
    CONTROLLED_CLAIM,
    load_programming_spec,
    run_clinical_programming_workflow,
)


def _write_qc(path: Path, passed: bool = True) -> None:
    pd.DataFrame(
        [{"check": "example", "passed": passed, "required": True, "detail": "fixture"}]
    ).to_csv(path, index=False)


def _fixture_root(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path
    (root / "spec").mkdir()
    (root / "scripts").mkdir()
    (root / "outputs").mkdir()

    (root / "scripts" / "prod.py").write_text("print('ok')\n", encoding="utf-8")
    (root / "spec" / "dataset.json").write_text("{}\n", encoding="utf-8")
    pd.DataFrame(
        [
            {"STUDYID": "S", "USUBJID": "01", "AVAL": 1.0},
            {"STUDYID": "S", "USUBJID": "02", "AVAL": 2.0},
        ]
    ).to_csv(root / "outputs" / "adsl.csv", index=False)
    _write_qc(root / "outputs" / "qc.csv", passed=True)
    (root / "outputs" / "manifest.json").write_text(
        json.dumps({"source_urls": {"dm": "https://example/dm.csv"}}),
        encoding="utf-8",
    )
    for name in ["change_impact_metrics.json", "traceability_metrics.json"]:
        (root / "outputs" / name).write_text(
            json.dumps({"all_passed": True}),
            encoding="utf-8",
        )
    spec_path = root / "spec" / "clinical_programming_workflow_v0_25.csv"
    pd.DataFrame(
        [
            {
                "program_id": "CP-001",
                "deliverable_type": "analysis_dataset",
                "deliverable": "ADSL-style fixture",
                "source_domains": "DM",
                "analysis_inputs": "",
                "output_path": "outputs/adsl.csv",
                "key_columns": "STUDYID;USUBJID",
                "required_columns": "STUDYID;USUBJID;AVAL",
                "production_programs": "scripts/prod.py",
                "specification_files": "spec/dataset.json",
                "qc_evidence": "outputs/qc.csv",
                "qc_mode": "cross_language_reconstruction",
            }
        ]
    ).to_csv(spec_path, index=False)
    return root, spec_path


def test_clinical_programming_workflow_passes_complete_fixture(tmp_path: Path) -> None:
    root, spec_path = _fixture_root(tmp_path)
    result = run_clinical_programming_workflow(root, spec_path)
    assert result.metrics["all_required_passed"] is True
    assert result.metrics["controlled_claim"] == CONTROLLED_CLAIM
    assert result.metrics["required_checks"] == result.metrics["required_passed"]
    assert len(result.release_manifest) == 1
    assert result.release_manifest.iloc[0]["output_rows"] == 2


def test_clinical_programming_workflow_blocks_duplicate_output_key(tmp_path: Path) -> None:
    root, spec_path = _fixture_root(tmp_path)
    pd.DataFrame(
        [
            {"STUDYID": "S", "USUBJID": "01", "AVAL": 1.0},
            {"STUDYID": "S", "USUBJID": "01", "AVAL": 2.0},
        ]
    ).to_csv(root / "outputs" / "adsl.csv", index=False)
    result = run_clinical_programming_workflow(root, spec_path)
    failed = result.checks.loc[~result.checks["passed"]]
    assert "Declared output key is unique" in failed["check"].tolist()
    assert result.metrics["all_required_passed"] is False
    assert result.metrics["controlled_claim"] == ""


def test_clinical_programming_workflow_blocks_failed_qc(tmp_path: Path) -> None:
    root, spec_path = _fixture_root(tmp_path)
    _write_qc(root / "outputs" / "qc.csv", passed=False)
    result = run_clinical_programming_workflow(root, spec_path)
    failed = result.checks.loc[~result.checks["passed"]]
    assert "Required QC evidence passes" in failed["check"].tolist()
    assert result.metrics["all_required_passed"] is False


def test_load_programming_spec_requires_control_columns(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    pd.DataFrame([{"program_id": "CP-001"}]).to_csv(path, index=False)
    with pytest.raises(ValueError, match="missing columns"):
        load_programming_spec(path)
