from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd


REVIEW_FILES = {
    "adsl": "adsl_style.csv",
    "adae": "adae_style.csv",
    "adqs": "adqs_actot_style.csv",
    "ancova": "ancova_analysis_subjects.csv",
    "mmrm": "mmrm_analysis_dataset.csv",
    "t1": "table1_demographics.csv",
    "t2": "table2_disposition.csv",
    "t4": "table4_teae_overview.csv",
    "t5": "table5_teae_soc_pt.csv",
    "t6": "table6_teae_severity.csv",
    "t7": "table7_teae_risk_difference.csv",
    "t8": "table8_actot_descriptive.csv",
    "t9": "table9_actot_lsmeans.csv",
    "t10": "table10_actot_ancova_contrasts.csv",
    "mmrm_visit_counts": "mmrm_visit_counts.csv",
    "mmrm_lsmeans": "mmrm_lsmeans.csv",
    "mmrm_contrasts": "mmrm_treatment_contrasts.csv",
}


def load_review_frames(output_dir: Path) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    missing: list[str] = []
    for name, filename in REVIEW_FILES.items():
        path = output_dir / filename
        if not path.exists():
            missing.append(filename)
            continue
        frames[name] = pd.read_csv(path)
    if missing:
        raise FileNotFoundError(f"Missing review inputs: {missing}")
    return frames


def _leading_int(value: object) -> int | None:
    match = re.match(r"\s*(\d+)", str(value))
    return int(match.group(1)) if match else None


def check_adae_adsl_consistency(adsl: pd.DataFrame, adae: pd.DataFrame) -> tuple[bool, str]:
    keys = ["STUDYID", "USUBJID"]
    ref = adsl[keys + ["TRT01A", "SAFFL", "TRTSDT", "TRTEDT"]].copy()
    merged = adae.merge(
        ref,
        on=keys,
        how="left",
        suffixes=("", "_ADSL"),
        indicator=True,
        validate="many_to_one",
    )
    missing_parent = int(merged["_merge"].ne("both").sum())
    treatment_mismatch = int(
        (
            merged["_merge"].eq("both")
            & merged["TRT01A"].fillna("<NA>").ne(merged["TRT01A_ADSL"].fillna("<NA>"))
        ).sum()
    )
    saffl_mismatch = int(
        (
            merged["_merge"].eq("both")
            & merged["SAFFL"].fillna("<NA>").ne(merged["SAFFL_ADSL"].fillna("<NA>"))
        ).sum()
    )
    treatment_date_mismatch = 0
    for column in ["TRTSDT", "TRTEDT"]:
        treatment_date_mismatch += int(
            (
                merged["_merge"].eq("both")
                & merged[column]
                .fillna("<NA>")
                .astype(str)
                .ne(merged[f"{column}_ADSL"].fillna("<NA>").astype(str))
            ).sum()
        )
    passed = missing_parent + treatment_mismatch + saffl_mismatch + treatment_date_mismatch == 0
    detail = (
        f"missing parent={missing_parent}; treatment mismatch={treatment_mismatch}; "
        f"SAFFL mismatch={saffl_mismatch}; treatment-date mismatch={treatment_date_mismatch}"
    )
    return passed, detail


def check_adqs_adsl_consistency(adsl: pd.DataFrame, adqs: pd.DataFrame) -> tuple[bool, str]:
    keys = ["STUDYID", "USUBJID"]
    ref = adsl[keys + ["TRT01A", "RANDFL"]].copy()
    merged = adqs.merge(
        ref,
        on=keys,
        how="left",
        suffixes=("", "_ADSL"),
        indicator=True,
        validate="many_to_one",
    )
    missing_parent = int(merged["_merge"].ne("both").sum())
    treatment_mismatch = int(
        (
            merged["_merge"].eq("both")
            & merged["TRT01A"].fillna("<NA>").ne(merged["TRT01A_ADSL"].fillna("<NA>"))
        ).sum()
    )
    non_randomised_records = int((merged["_merge"].eq("both") & merged["RANDFL"].ne("Y")).sum())
    passed = missing_parent + treatment_mismatch + non_randomised_records == 0
    detail = (
        f"missing parent={missing_parent}; treatment mismatch={treatment_mismatch}; "
        f"non-randomised records={non_randomised_records}"
    )
    return passed, detail


def check_actot_baseline_consistency(adqs: pd.DataFrame) -> tuple[bool, str]:
    keys = ["STUDYID", "USUBJID"]
    efficacy = adqs.loc[adqs["EFFFL"].eq("Y")].copy()
    efficacy_subjects = efficacy[keys].drop_duplicates()
    baselines = (
        adqs.loc[adqs["ABLFL"].eq("Y"), keys + ["AVAL"]]
        .rename(columns={"AVAL": "BASE_FROM_ROW"})
        .copy()
    )
    baseline_counts = baselines.groupby(keys, dropna=False).size()
    multiple_baselines = int((baseline_counts > 1).sum())
    subject_check = efficacy_subjects.merge(baselines, on=keys, how="left")
    missing_baseline = int(subject_check["BASE_FROM_ROW"].isna().sum())
    joined = efficacy.merge(baselines, on=keys, how="left", validate="many_to_one")
    base_mismatch = int(
        (~np.isclose(
            pd.to_numeric(joined["BASE"], errors="coerce"),
            pd.to_numeric(joined["BASE_FROM_ROW"], errors="coerce"),
            atol=1e-10,
            rtol=0,
            equal_nan=True,
        )).sum()
    )
    chg_mismatch = int(
        (~np.isclose(
            pd.to_numeric(efficacy["CHG"], errors="coerce"),
            pd.to_numeric(efficacy["AVAL"], errors="coerce") - pd.to_numeric(efficacy["BASE"], errors="coerce"),
            atol=1e-10,
            rtol=0,
            equal_nan=True,
        )).sum()
    )
    passed = multiple_baselines + missing_baseline + base_mismatch + chg_mismatch == 0
    detail = (
        f"multiple baselines={multiple_baselines}; efficacy subjects missing baseline={missing_baseline}; "
        f"BASE mismatch={base_mismatch}; CHG mismatch={chg_mismatch}"
    )
    return passed, detail


def check_mmrm_source_consistency(adqs: pd.DataFrame, mmrm: pd.DataFrame) -> tuple[bool, str]:
    keys = ["STUDYID", "USUBJID", "QSSEQ"]
    ref = adqs[keys + ["TRT01A", "AVAL", "BASE", "CHG"]].copy()
    merged = mmrm.merge(
        ref,
        on=keys,
        how="left",
        suffixes=("", "_SRC"),
        indicator=True,
        validate="many_to_one",
    )
    missing_source = int(merged["_merge"].ne("both").sum())
    treatment_mismatch = int(
        (
            merged["_merge"].eq("both")
            & merged["TRT01A"].fillna("<NA>").ne(merged["TRT01A_SRC"].fillna("<NA>"))
        ).sum()
    )
    numeric_mismatch = 0
    for column in ["AVAL", "BASE", "CHG"]:
        numeric_mismatch += int(
            (~np.isclose(
                pd.to_numeric(merged[column], errors="coerce"),
                pd.to_numeric(merged[f"{column}_SRC"], errors="coerce"),
                atol=1e-10,
                rtol=0,
                equal_nan=True,
            )).sum()
        )
    passed = missing_source + treatment_mismatch + numeric_mismatch == 0
    detail = (
        f"missing source rows={missing_source}; treatment mismatch={treatment_mismatch}; "
        f"numeric field mismatches={numeric_mismatch}"
    )
    return passed, detail


def check_safety_table_denominators(
    adsl: pd.DataFrame,
    table5: pd.DataFrame,
    table6: pd.DataFrame,
) -> tuple[bool, str]:
    safety_n = (
        adsl.loc[adsl["SAFFL"].eq("Y")]
        .groupby("TRT01A")["USUBJID"]
        .nunique()
        .to_dict()
    )
    bad_table5 = int(
        sum(int(row.denom) != int(safety_n.get(row.TRT01A, -1)) for row in table5.itertuples())
    )
    bad_table6 = int(
        sum(int(row.denom) != int(safety_n.get(row.TRT01A, -1)) for row in table6.itertuples())
    )
    passed = bad_table5 + bad_table6 == 0
    detail = f"table5 bad denominators={bad_table5}; table6 bad denominators={bad_table6}; expected={safety_n}"
    return passed, detail


def review_frames(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    checks: list[dict[str, object]] = []

    def add(check: str, passed: bool, detail: str, area: str) -> None:
        checks.append({"check": check, "passed": bool(passed), "required": True, "area": area, "detail": detail})

    adsl = frames["adsl"]
    adae = frames["adae"]
    adqs = frames["adqs"]
    ancova = frames["ancova"]
    mmrm = frames["mmrm"]

    duplicate_subjects = int(adsl.duplicated(["STUDYID", "USUBJID"]).sum())
    add(
        "ADSL-style subject key is unique",
        duplicate_subjects == 0,
        f"duplicates={duplicate_subjects}",
        "analysis_dataset",
    )

    safety_not_randomised = int((adsl["SAFFL"].eq("Y") & adsl["RANDFL"].ne("Y")).sum())
    add(
        "Safety population is a subset of randomised population",
        safety_not_randomised == 0,
        f"violating subjects={safety_not_randomised}",
        "population",
    )

    passed, detail = check_adae_adsl_consistency(adsl, adae)
    add("ADAE-style subject attributes reconcile to ADSL-style", passed, detail, "analysis_dataset")

    passed, detail = check_adqs_adsl_consistency(adsl, adqs)
    add("ACTOT analysis records reconcile to ADSL-style", passed, detail, "analysis_dataset")

    passed, detail = check_actot_baseline_consistency(adqs)
    add("ACTOT baseline and change derivations reconcile", passed, detail, "derivation")

    subject_keys = ["STUDYID", "USUBJID"]
    ancova_join = ancova.merge(
        adsl[subject_keys + ["TRT01A"]],
        on=subject_keys,
        how="left",
        suffixes=("", "_ADSL"),
        indicator=True,
        validate="many_to_one",
    )
    ancova_treatment_bad = int(ancova_join["_merge"].ne("both").sum()) + int(
        ancova_join["TRT01A"].fillna("<NA>").ne(ancova_join["TRT01A_ADSL"].fillna("<NA>")).sum()
    )
    add(
        "ANCOVA analysis-subject treatment reconciles to ADSL-style",
        ancova_treatment_bad == 0,
        f"missing/treatment mismatches={ancova_treatment_bad}",
        "analysis_dataset",
    )

    ancova_chg_bad = int(
        (~np.isclose(
            pd.to_numeric(ancova["CHG"], errors="coerce"),
            pd.to_numeric(ancova["AVAL"], errors="coerce") - pd.to_numeric(ancova["BASE"], errors="coerce"),
            atol=1e-10,
            rtol=0,
            equal_nan=True,
        )).sum()
    )
    add(
        "ANCOVA CHG equals AVAL minus BASE",
        ancova_chg_bad == 0,
        f"mismatches={ancova_chg_bad}",
        "derivation",
    )

    passed, detail = check_mmrm_source_consistency(adqs, mmrm)
    add("MMRM rows trace to exact ACTOT source records", passed, detail, "analysis_dataset")

    mmrm_duplicate_visit = int(mmrm.duplicated(["STUDYID", "USUBJID", "AVISIT"]).sum())
    invalid_visits = sorted(set(mmrm["AVISIT"].dropna()) - {"Week 8", "Week 16", "Week 24"})
    add(
        "MMRM subject-visit key and visit set are valid",
        mmrm_duplicate_visit == 0 and not invalid_visits,
        f"duplicate subject-visits={mmrm_duplicate_visit}; invalid visits={invalid_visits}",
        "analysis_dataset",
    )

    randomised_n = (
        adsl.loc[adsl["RANDFL"].eq("Y")]
        .groupby("TRT01A")["USUBJID"]
        .nunique()
        .to_dict()
    )
    safety_n = (
        adsl.loc[adsl["SAFFL"].eq("Y")]
        .groupby("TRT01A")["USUBJID"]
        .nunique()
        .to_dict()
    )

    table1_n = {
        row.TRT01A: _leading_int(row.Value)
        for row in frames["t1"].loc[frames["t1"]["Statistic"].eq("N")].itertuples()
    }
    add(
        "Demographics N reconciles to randomised population",
        table1_n == randomised_n,
        f"table={table1_n}; expected={randomised_n}",
        "tlf_denominator",
    )

    table2 = frames["t2"]
    table2_randomised = {
        row.TRT01A: _leading_int(row.Value)
        for row in table2.loc[table2["Statistic"].eq("Randomised N")].itertuples()
    }
    table2_safety = {
        row.TRT01A: _leading_int(row.Value)
        for row in table2.loc[table2["Statistic"].eq("Safety population, n (%)")].itertuples()
    }
    add(
        "Disposition randomised and safety denominators reconcile",
        table2_randomised == randomised_n and table2_safety == safety_n,
        (
            f"randomised={table2_randomised}; safety={table2_safety}; "
            f"expected randomised={randomised_n}; expected safety={safety_n}"
        ),
        "tlf_denominator",
    )

    teae = adae.loc[adae["TRTEMFL"].eq("Y")].copy()
    teae_subject_n = {
        arm: int(teae.loc[teae["TRT01A"].eq(arm), "USUBJID"].nunique())
        for arm in safety_n
    }
    teae_event_n = {
        arm: int(teae["TRT01A"].eq(arm).sum())
        for arm in safety_n
    }
    table4 = frames["t4"]
    table4_safety = {
        row.TRT01A: _leading_int(row.Value)
        for row in table4.loc[table4["Statistic"].eq("Safety N")].itertuples()
    }
    table4_teae_subject = {
        row.TRT01A: _leading_int(row.Value)
        for row in table4.loc[table4["Statistic"].eq("Subjects with >=1 TEAE, n (%)")].itertuples()
    }
    table4_teae_event = {
        row.TRT01A: _leading_int(row.Value)
        for row in table4.loc[table4["Statistic"].eq("Total TEAE events")].itertuples()
    }
    add(
        "TEAE overview counts reconcile to ADAE-style and safety population",
        table4_safety == safety_n and table4_teae_subject == teae_subject_n and table4_teae_event == teae_event_n,
        f"safety={table4_safety}; subject counts={table4_teae_subject}; event counts={table4_teae_event}",
        "tlf_denominator",
    )

    passed, detail = check_safety_table_denominators(adsl, frames["t5"], frames["t6"])
    add("SOC/PT and severity denominators reconcile to safety population", passed, detail, "tlf_denominator")

    table7_bad = 0
    placebo_n = safety_n.get("Placebo", -1)
    teae_risk = {arm: teae_subject_n[arm] / safety_n[arm] for arm in safety_n}
    for row in frames["t7"].itertuples():
        arm = str(row.comparison).replace(" vs Placebo", "")
        if int(row.n_arm) != safety_n.get(arm, -1) or int(row.n_placebo) != placebo_n:
            table7_bad += 1
        if arm in teae_risk:
            if abs(float(row.risk_arm) - teae_risk[arm]) > 5e-5:
                table7_bad += 1
            if abs(float(row.risk_placebo) - teae_risk["Placebo"]) > 5e-5:
                table7_bad += 1
    add(
        "TEAE risk-difference denominators and risks reconcile",
        table7_bad == 0,
        f"mismatch conditions={table7_bad}",
        "tlf_denominator",
    )

    ancova_n = ancova.groupby(["analysis", "TRT01A"])["USUBJID"].nunique().to_dict()
    table8_n = {row.TRT01A: int(row.n) for row in frames["t8"].itertuples()}
    expected_table8 = {
        arm: n for (analysis, arm), n in ancova_n.items() if analysis == "Observed Week 24"
    }
    add(
        "Week 24 descriptive N reconciles to observed ANCOVA set",
        table8_n == expected_table8,
        f"table={table8_n}; expected={expected_table8}",
        "tlf_denominator",
    )

    table9_n = {(row.analysis, row.TRT01A): int(row.n) for row in frames["t9"].itertuples()}
    add(
        "ANCOVA LS-mean N reconciles to analysis-subject sets",
        table9_n == ancova_n,
        f"table rows={len(table9_n)}; expected rows={len(ancova_n)}",
        "tlf_denominator",
    )

    analysis_totals = ancova.groupby("analysis")["USUBJID"].nunique().to_dict()
    table10_bad = int(
        sum(int(row.n_total) != int(analysis_totals.get(row.analysis, -1)) for row in frames["t10"].itertuples())
    )
    add(
        "ANCOVA contrast total N reconciles to analysis-subject sets",
        table10_bad == 0,
        f"mismatch rows={table10_bad}; expected totals={analysis_totals}",
        "tlf_denominator",
    )

    expected_visit_counts = mmrm.groupby(["AVISIT", "TRT01A"]).size().to_dict()
    reported_visit_counts = {
        (row.AVISIT, row.TRT01A): int(row.records)
        for row in frames["mmrm_visit_counts"].itertuples()
    }
    add(
        "MMRM visit-count output reconciles to MMRM analysis dataset",
        reported_visit_counts == expected_visit_counts,
        f"table rows={len(reported_visit_counts)}; expected rows={len(expected_visit_counts)}",
        "tlf_denominator",
    )

    lsmean_keys = set(
        map(tuple, frames["mmrm_lsmeans"][["AVISIT", "TRT01A"]].itertuples(index=False, name=None))
    )
    expected_lsmeans = {
        (visit, arm)
        for visit in ["Week 8", "Week 16", "Week 24"]
        for arm in ["Placebo", "Xanomeline Low Dose", "Xanomeline High Dose"]
    }
    contrast_keys = set(
        map(tuple, frames["mmrm_contrasts"][["AVISIT", "contrast"]].itertuples(index=False, name=None))
    )
    expected_contrasts = {
        (visit, contrast)
        for visit in ["Week 8", "Week 16", "Week 24"]
        for contrast in ["Xanomeline Low Dose vs Placebo", "Xanomeline High Dose vs Placebo"]
    }
    add(
        "MMRM LS means and active-vs-placebo contrasts have complete visit coverage",
        lsmean_keys == expected_lsmeans and contrast_keys == expected_contrasts,
        f"LS means={len(lsmean_keys)}/9; contrasts={len(contrast_keys)}/6",
        "tlf_structure",
    )

    return pd.DataFrame(checks)


def run_dataset_review(output_dir: Path) -> pd.DataFrame:
    return review_frames(load_review_frames(output_dir))
