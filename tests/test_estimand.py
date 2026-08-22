import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.estimand import derive_actot_missingness, review_estimand_consistency, validate_estimand_spec


def _spec():
    return {
        "estimands": [{
            "id": "EST-ACTOT-W24-TP",
            "treatment": {"conditions": ["Placebo", "Xanomeline Low Dose", "Xanomeline High Dose"]},
            "population": {"operational_rule": "RANDFL=Y and baseline ACTOT observed"},
            "variable": {"parameter": "ACTOT", "visit": "Week 24", "measure": "change_from_baseline"},
            "intercurrent_events": [{"event": "treatment_discontinuation", "strategy": "treatment_policy"}],
            "summary_measure": {"type": "active_vs_placebo_difference_in_adjusted_mean_change"},
            "estimator": {"primary": {"method": "MMRM", "uses_locf": False, "missing_data_assumption": "MAR"}},
        }]
    }


def _frames():
    arms = ["Placebo", "Xanomeline Low Dose", "Xanomeline High Dose"]
    adsl_rows = []
    adqs_rows = []
    mmrm_rows = []
    for i, arm in enumerate(arms, start=1):
        subj = f"S{i}"
        dcs = "Y" if arm == "Xanomeline Low Dose" else "N"
        eos = "2026-02-20" if dcs == "Y" else "2026-08-01"
        adsl_rows.append({
            "STUDYID": "ST", "USUBJID": subj, "TRT01A": arm, "RANDFL": "Y", "DCSFL": dcs,
            "EOSDECOD": "WITHDRAWAL BY SUBJECT" if dcs == "Y" else "COMPLETED", "EOSDT": eos, "TRTSDT": "2026-01-01",
        })
        adqs_rows.append({
            "STUDYID": "ST", "USUBJID": subj, "TRT01A": arm, "AVISIT": "Baseline", "AVAL": 20 + i,
            "BASE": 20 + i, "CHG": 0, "ABLFL": "Y", "EFFFL": "Y", "ADT": "2026-01-01",
        })
        for visit, day, date in [("Week 8", 56, "2026-02-25"), ("Week 16", 112, "2026-04-22"), ("Week 24", 168, "2026-06-17")]:
            if arm == "Xanomeline High Dose" and visit == "Week 24":
                continue
            aval = 20 + i + day / 100
            row = {
                "STUDYID": "ST", "USUBJID": subj, "TRT01A": arm, "AVISIT": visit, "AVAL": aval,
                "BASE": 20 + i, "CHG": aval - (20 + i), "ABLFL": "", "EFFFL": "Y", "ADT": date,
            }
            adqs_rows.append(row)
            mmrm_rows.append({k: row[k] for k in ["STUDYID", "USUBJID", "TRT01A", "AVISIT", "AVAL", "BASE", "CHG"]})
    return pd.DataFrame(adsl_rows), pd.DataFrame(adqs_rows), pd.DataFrame(mmrm_rows)


def test_estimand_spec_accepts_complete_treatment_policy_estimand():
    checks = validate_estimand_spec(_spec())
    assert checks.loc[checks["required"], "passed"].all()


def test_estimand_spec_rejects_locf_as_primary_estimator():
    spec = _spec()
    spec["estimands"][0]["estimator"]["primary"]["uses_locf"] = True
    checks = validate_estimand_spec(spec)
    bad = checks.loc[checks["check"].str.contains("does not use LOCF")]
    assert len(bad) == 1 and not bool(bad.iloc[0]["passed"])


def test_missingness_reconciles_arm_visit_denominators():
    adsl, adqs, _ = _frames()
    missing, patterns, reasons = derive_actot_missingness(adsl, adqs)
    assert len(missing) == 9
    assert (missing["observed_n"] + missing["missing_n"] == missing["target_n"]).all()
    high24 = missing.loc[(missing["TRT01A"] == "Xanomeline High Dose") & (missing["AVISIT"] == "Week 24")].iloc[0]
    assert high24["missing_n"] == 1
    assert patterns.loc[patterns["TRT01A"] == "Xanomeline High Dose", "PATTERN"].iloc[0] == "OOM"
    assert reasons.loc[reasons["TRT01A"] == "Xanomeline High Dose", "n"].sum() == 1


def test_missingness_identifies_observed_post_discontinuation_record():
    adsl, adqs, _ = _frames()
    missing, _, _ = derive_actot_missingness(adsl, adqs)
    low8 = missing.loc[(missing["TRT01A"] == "Xanomeline Low Dose") & (missing["AVISIT"] == "Week 8")].iloc[0]
    assert low8["observed_after_discontinuation_n"] == 1


def test_estimand_review_accepts_observed_data_mmrm_and_retains_post_discontinuation():
    adsl, adqs, mmrm = _frames()
    missing, _, reasons = derive_actot_missingness(adsl, adqs)
    checks = review_estimand_consistency(_spec(), adsl, adqs, mmrm, missing, reasons)
    assert checks.loc[checks["required"], "passed"].all()


def test_estimand_review_fails_if_post_discontinuation_observation_removed_from_mmrm():
    adsl, adqs, mmrm = _frames()
    mmrm = mmrm.loc[~((mmrm["USUBJID"] == "S2") & (mmrm["AVISIT"] == "Week 8"))].copy()
    missing, _, reasons = derive_actot_missingness(adsl, adqs)
    checks = review_estimand_consistency(_spec(), adsl, adqs, mmrm, missing, reasons)
    assert not checks.loc[checks["check"].eq("Observed post-discontinuation ACTOT records are retained"), "passed"].iloc[0]


def test_estimand_review_fails_when_missingness_denominator_is_corrupted():
    adsl, adqs, mmrm = _frames()
    missing, _, reasons = derive_actot_missingness(adsl, adqs)
    missing.loc[0, "target_n"] += 1
    checks = review_estimand_consistency(_spec(), adsl, adqs, mmrm, missing, reasons)
    assert not checks.loc[checks["check"].eq("Observed plus missing equals target denominator"), "passed"].iloc[0]
