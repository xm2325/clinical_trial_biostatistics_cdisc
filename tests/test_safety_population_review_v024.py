from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from cdisc_portfolio.safety_population_review import run_safety_population_review


def _fixture(tmp_path: Path) -> Path:
    (tmp_path / "spec").mkdir()
    (tmp_path / "outputs").mkdir()
    cfg = {
        "version": "0.24.0",
        "claim": "PORTFOLIO_SAFETY_POPULATION_ASSIGNMENT_READY",
        "safety_flag": "SAFFL",
        "safety_assignment": "TRT01A",
        "efficacy_assignment_context": "TRT01P",
        "teae_flag": "TRTEMFL",
        "rules": [],
        "interpretation_boundary": ["test"]
    }
    (tmp_path / "spec" / "safety_population_review_v0_24.json").write_text(json.dumps(cfg))
    pd.DataFrame([
        {"USUBJID": "P", "SAFFL": "Y", "TRT01P": "Placebo", "TRT01A": "Placebo"},
        {"USUBJID": "L", "SAFFL": "Y", "TRT01P": "Xanomeline Low Dose", "TRT01A": "Xanomeline Low Dose"},
        {"USUBJID": "H1", "SAFFL": "Y", "TRT01P": "Xanomeline High Dose", "TRT01A": "Xanomeline High Dose"},
        {"USUBJID": "H2", "SAFFL": "Y", "TRT01P": "Xanomeline High Dose", "TRT01A": "Xanomeline Low Dose"}
    ]).to_csv(tmp_path / "outputs" / "adsl_style.csv", index=False)
    pd.DataFrame([
        {"USUBJID": "P", "TRT01A": "Placebo", "TRTEMFL": "Y"},
        {"USUBJID": "L", "TRT01A": "Xanomeline Low Dose", "TRTEMFL": "Y"},
        {"USUBJID": "L", "TRT01A": "Xanomeline Low Dose", "TRTEMFL": "Y"},
        {"USUBJID": "H2", "TRT01A": "Xanomeline Low Dose", "TRTEMFL": "Y"}
    ]).to_csv(tmp_path / "outputs" / "adae_style.csv", index=False)
    pd.DataFrame([
        {"comparison": "Xanomeline Low Dose vs Placebo", "n_arm": 2, "n_placebo": 1},
        {"comparison": "Xanomeline High Dose vs Placebo", "n_arm": 1, "n_placebo": 1}
    ]).to_csv(tmp_path / "outputs" / "table7_teae_risk_difference.csv", index=False)
    return tmp_path


def test_safety_review_uses_actual_treatment_and_subject_incidence(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    provenance, comparison, checks, metrics = run_safety_population_review(root)
    assert metrics["all_passed"] is True
    assert metrics["planned_actual_mismatch_safety_subjects"] == 1
    assert metrics["teae_events"] == 4
    assert metrics["subjects_with_teae"] == 3
    low = comparison.loc[comparison["arm"].eq("Xanomeline Low Dose")].iloc[0]
    high = comparison.loc[comparison["arm"].eq("Xanomeline High Dose")].iloc[0]
    assert int(low["safety_n_actual"]) == 2
    assert int(low["safety_n_planned"]) == 1
    assert int(high["safety_n_actual"]) == 1
    assert int(high["safety_n_planned"]) == 2
    assert int(provenance.loc[provenance["USUBJID"].eq("L"), "teae_event_count"].iloc[0]) == 2
    assert checks["passed"].all()


def test_safety_review_blocks_adae_assignment_drift(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    adae = pd.read_csv(root / "outputs" / "adae_style.csv")
    adae.loc[adae["USUBJID"].eq("H2"), "TRT01A"] = "Xanomeline High Dose"
    adae.to_csv(root / "outputs" / "adae_style.csv", index=False)
    _, _, checks, metrics = run_safety_population_review(root)
    assert metrics["all_passed"] is False
    row = checks.loc[checks["check"].eq("adae_assignment_matches_adsl_actual")].iloc[0]
    assert bool(row["passed"]) is False
