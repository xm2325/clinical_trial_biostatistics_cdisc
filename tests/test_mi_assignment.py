from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from cdisc_portfolio.mi_assignment import build_mi_assignment_inputs, assess_mi_assignment_outputs


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _fixture(tmp_path: Path) -> Path:
    (tmp_path / "spec").mkdir()
    (tmp_path / "outputs").mkdir()
    cfg = {
        "version": "0.23.0",
        "assignment_claim": "PORTFOLIO_RANDOMISED_ASSIGNMENT_CONSISTENCY_READY",
        "mi_assignment_source": "TRT01P",
        "actual_treatment_context": "TRT01A",
        "required_arms": ["Placebo", "Xanomeline Low Dose", "Xanomeline High Dose"],
        "expected_randomised_counts": {"Placebo": 1, "Xanomeline Low Dose": 1, "Xanomeline High Dose": 1},
        "expected_randomised_subjects": 3,
        "expected_baseline_subjects": 3,
        "expected_assignment_mismatches": 1,
        "expected_mismatch_transition": {"planned": "Xanomeline High Dose", "actual": "Xanomeline Low Dose"},
        "expected_primary_mmrm_subjects": 2,
        "expected_week24_observed": 1,
        "expected_week24_missing": 2,
        "expected_pairwise_mi_target_n": 2,
        "rules": {
            "mi_uses_planned_randomised_assignment": True,
            "actual_treatment_is_preserved_as_context": True,
            "randomised_baseline_population_is_complete": True,
            "mismatch_subjects_in_primary_mmrm_are_blocking": True,
            "pairwise_mi_target_counts_must_reconcile": True,
        },
        "evidence_boundary": "test portfolio boundary",
    }
    _write_json(tmp_path / "spec" / "mi_assignment_v0_23.json", cfg)

    pd.DataFrame([
        {"STUDYID": "S", "USUBJID": "P", "TRT01P": "Placebo", "TRT01A": "Placebo", "RANDFL": "Y", "SAFFL": "Y"},
        {"STUDYID": "S", "USUBJID": "L", "TRT01P": "Xanomeline Low Dose", "TRT01A": "Xanomeline Low Dose", "RANDFL": "Y", "SAFFL": "Y"},
        {"STUDYID": "S", "USUBJID": "H", "TRT01P": "Xanomeline High Dose", "TRT01A": "Xanomeline Low Dose", "RANDFL": "Y", "SAFFL": "Y"},
        {"STUDYID": "S", "USUBJID": "N", "TRT01P": "Screen Failure", "TRT01A": "Screen Failure", "RANDFL": "N", "SAFFL": "N"},
    ]).to_csv(tmp_path / "outputs" / "adsl_style.csv", index=False)

    rows = []
    for sid, actual, base in [("P", "Placebo", 10.0), ("L", "Xanomeline Low Dose", 11.0), ("H", "Xanomeline Low Dose", 12.0)]:
        rows.append({"STUDYID": "S", "USUBJID": sid, "TRT01A": actual, "ABLFL": "Y", "EFFFL": "Y", "AVISIT": "Baseline", "AVAL": base, "BASE": base, "CHG": 0.0})
    rows += [
        {"STUDYID": "S", "USUBJID": "P", "TRT01A": "Placebo", "ABLFL": "", "EFFFL": "Y", "AVISIT": "Week 8", "AVAL": 9.0, "BASE": 10.0, "CHG": -1.0},
        {"STUDYID": "S", "USUBJID": "P", "TRT01A": "Placebo", "ABLFL": "", "EFFFL": "Y", "AVISIT": "Week 24", "AVAL": 8.0, "BASE": 10.0, "CHG": -2.0},
        {"STUDYID": "S", "USUBJID": "L", "TRT01A": "Xanomeline Low Dose", "ABLFL": "", "EFFFL": "Y", "AVISIT": "Week 8", "AVAL": 10.0, "BASE": 11.0, "CHG": -1.0},
    ]
    pd.DataFrame(rows).to_csv(tmp_path / "outputs" / "adqs_actot_style.csv", index=False)

    pd.DataFrame([
        {"STUDYID": "S", "USUBJID": "P", "TRT01A": "Placebo", "AVISIT": "Week 8"},
        {"STUDYID": "S", "USUBJID": "P", "TRT01A": "Placebo", "AVISIT": "Week 24"},
        {"STUDYID": "S", "USUBJID": "L", "TRT01A": "Xanomeline Low Dose", "AVISIT": "Week 8"},
    ]).to_csv(tmp_path / "outputs" / "mmrm_analysis_dataset.csv", index=False)
    return tmp_path


def test_planned_assignment_builder_preserves_actual_context(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    metrics = build_mi_assignment_inputs(root)
    assert metrics["all_passed"] is True
    assert metrics["assignment_mismatches"] == 1
    assert metrics["mismatch_primary_mmrm_subjects"] == 0
    assert metrics["pairwise_mi_target_counts"] == {"LOW_VS_PLACEBO": 2, "HIGH_VS_PLACEBO": 2}
    adsl_mi = pd.read_csv(root / "outputs" / "adsl_mi_planned.csv")
    high = adsl_mi.loc[adsl_mi["USUBJID"].eq("H")].iloc[0]
    assert high["TRT01A"] == "Xanomeline High Dose"
    assert high["TRT01A_ACTUAL"] == "Xanomeline Low Dose"


def test_mismatch_subject_entering_primary_mmrm_blocks_builder(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    mmrm = pd.read_csv(root / "outputs" / "mmrm_analysis_dataset.csv")
    mmrm.loc[len(mmrm)] = {"STUDYID": "S", "USUBJID": "H", "TRT01A": "Xanomeline Low Dose", "AVISIT": "Week 8"}
    mmrm.to_csv(root / "outputs" / "mmrm_analysis_dataset.csv", index=False)
    try:
        build_mi_assignment_inputs(root)
    except ValueError as exc:
        assert "MI assignment input gate failed" in str(exc)
    else:
        raise AssertionError("mismatch subject in primary MMRM should be blocking")


def test_planned_randomisation_count_drift_blocks_builder(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    adsl = pd.read_csv(root / "outputs" / "adsl_style.csv")
    adsl.loc[adsl["USUBJID"].eq("L"), "TRT01P"] = "Xanomeline High Dose"
    adsl.to_csv(root / "outputs" / "adsl_style.csv", index=False)
    try:
        build_mi_assignment_inputs(root)
    except ValueError as exc:
        assert "MI assignment input gate failed" in str(exc)
    else:
        raise AssertionError("planned randomisation count drift should be blocking")


def test_executed_pairwise_target_count_drift_blocks_post_mi_audit(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    build_mi_assignment_inputs(root)
    pd.DataFrame([
        {"comparison_id": "LOW_VS_PLACEBO", "visit": 8, "target_n": 2},
        {"comparison_id": "LOW_VS_PLACEBO", "visit": 16, "target_n": 2},
        {"comparison_id": "LOW_VS_PLACEBO", "visit": 24, "target_n": 2},
        {"comparison_id": "HIGH_VS_PLACEBO", "visit": 8, "target_n": 3},
        {"comparison_id": "HIGH_VS_PLACEBO", "visit": 16, "target_n": 3},
        {"comparison_id": "HIGH_VS_PLACEBO", "visit": 24, "target_n": 3},
    ]).to_csv(root / "outputs" / "rbmi_pairwise_input_counts.csv", index=False)
    ref_rows = []
    for cmp in ["LOW_VS_PLACEBO", "HIGH_VS_PLACEBO"]:
        for strategy in ["MAR", "JR", "CR", "CIR"]:
            ref_rows.append({"comparison_id": cmp, "strategy_id": strategy, "mcse_pass": True})
    pd.DataFrame(ref_rows).to_csv(root / "outputs" / "table22_rbmi_reference_based.csv", index=False)
    try:
        assess_mi_assignment_outputs(root)
    except ValueError as exc:
        assert "executed MI assignment audit failed" in str(exc)
    else:
        raise AssertionError("executed pairwise target drift should be blocking")
