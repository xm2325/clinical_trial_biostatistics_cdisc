from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

VERSION = "0.23.0"
CLAIM = "PORTFOLIO_RANDOMISED_ASSIGNMENT_CONSISTENCY_READY"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _check(checks: list[dict[str, Any]], name: str, passed: bool, detail: str) -> None:
    checks.append({"check": name, "passed": bool(passed), "required": True, "detail": detail})


def _require(df: pd.DataFrame, columns: set[str], label: str) -> None:
    missing = sorted(columns.difference(df.columns))
    if missing:
        raise ValueError(f"{label} missing required columns: {missing}")


def _validate_cfg(cfg: dict[str, Any]) -> None:
    if cfg.get("version") != VERSION:
        raise ValueError("MI assignment contract must be version 0.23.0")
    if cfg.get("assignment_claim") != CLAIM:
        raise ValueError("MI assignment claim must remain portfolio-scoped")
    if cfg.get("mi_assignment_source") != "TRT01P":
        raise ValueError("v0.23 MI grouping must use planned randomised assignment TRT01P")
    if cfg.get("actual_treatment_context") != "TRT01A":
        raise ValueError("v0.23 must preserve TRT01A as actual-treatment context")
    rules = cfg.get("rules", {})
    required_rules = {
        "mi_uses_planned_randomised_assignment",
        "actual_treatment_is_preserved_as_context",
        "randomised_baseline_population_is_complete",
        "mismatch_subjects_in_primary_mmrm_are_blocking",
        "pairwise_mi_target_counts_must_reconcile",
    }
    if set(rules) != required_rules or not all(bool(rules[k]) for k in required_rules):
        raise ValueError("all v0.23 MI assignment rules must remain enabled")


def build_mi_assignment_inputs(root: Path) -> dict[str, Any]:
    root = Path(root)
    cfg = _load_json(root / "spec" / "mi_assignment_v0_23.json")
    _validate_cfg(cfg)
    outputs = root / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)

    adsl = pd.read_csv(outputs / "adsl_style.csv")
    adqs = pd.read_csv(outputs / "adqs_actot_style.csv")
    mmrm = pd.read_csv(outputs / "mmrm_analysis_dataset.csv")
    _require(adsl, {"STUDYID", "USUBJID", "TRT01P", "TRT01A", "RANDFL", "SAFFL"}, "ADSL-style")
    _require(adqs, {"STUDYID", "USUBJID", "TRT01A", "ABLFL", "EFFFL", "AVISIT", "AVAL", "BASE", "CHG"}, "ADQS ACTOT-style")
    _require(mmrm, {"STUDYID", "USUBJID", "TRT01A", "AVISIT"}, "MMRM analysis dataset")

    checks: list[dict[str, Any]] = []
    adsl_key = adsl["STUDYID"].astype(str) + "|" + adsl["USUBJID"].astype(str)
    _check(checks, "ADSL-style subject key is unique", not adsl_key.duplicated().any(), f"duplicate_subjects={int(adsl_key.duplicated().sum())}")

    rand = adsl.loc[adsl["RANDFL"].astype(str).eq("Y")].copy()
    expected_counts = {str(k): int(v) for k, v in cfg["expected_randomised_counts"].items()}
    planned_counts = rand.groupby("TRT01P")["USUBJID"].nunique().to_dict()
    actual_counts = rand.groupby("TRT01A")["USUBJID"].nunique().to_dict()
    planned_counts_norm = {arm: int(planned_counts.get(arm, 0)) for arm in cfg["required_arms"]}
    _check(
        checks,
        "randomised planned-treatment counts match the controlled allocation",
        planned_counts_norm == expected_counts and len(rand) == int(cfg["expected_randomised_subjects"]),
        f"planned={planned_counts_norm}; total={len(rand)}",
    )

    baseline = adqs.loc[adqs["ABLFL"].astype(str).eq("Y") & pd.to_numeric(adqs["AVAL"], errors="coerce").notna()].copy()
    baseline = baseline.sort_values(["STUDYID", "USUBJID"]).drop_duplicates(["STUDYID", "USUBJID"], keep="last")
    baseline_ids = set(baseline["USUBJID"].astype(str))
    rand_ids = set(rand["USUBJID"].astype(str))
    baseline_rand = rand_ids.intersection(baseline_ids)
    _check(
        checks,
        "randomised baseline-ACTOT population is complete",
        len(baseline_rand) == int(cfg["expected_baseline_subjects"]),
        f"baseline_randomised={len(baseline_rand)}/{len(rand_ids)}",
    )

    mismatch = rand.loc[rand["TRT01P"].astype(str) != rand["TRT01A"].astype(str)].copy()
    transition = cfg["expected_mismatch_transition"]
    transition_ok = (
        len(mismatch) == int(cfg["expected_assignment_mismatches"])
        and set(mismatch["TRT01P"].astype(str)) == {str(transition["planned"])}
        and set(mismatch["TRT01A"].astype(str)) == {str(transition["actual"])}
    )
    _check(
        checks,
        "planned-versus-actual assignment mismatches match the controlled public-data issue",
        transition_ok,
        f"mismatches={len(mismatch)}; transitions={mismatch.groupby(['TRT01P','TRT01A']).size().to_dict()}",
    )

    mmrm_ids = set(mmrm["USUBJID"].astype(str))
    mismatch_ids = set(mismatch["USUBJID"].astype(str))
    mismatch_mmrm = mismatch_ids.intersection(mmrm_ids)
    _check(
        checks,
        "planned-versus-actual mismatch subjects do not enter the current observed primary MMRM",
        not mismatch_mmrm,
        f"mismatch_mmrm_subjects={len(mismatch_mmrm)}",
    )
    _check(
        checks,
        "primary MMRM subject count reconciles",
        len(mmrm_ids) == int(cfg["expected_primary_mmrm_subjects"]),
        f"mmrm_subjects={len(mmrm_ids)}",
    )

    # Reconcile ADQS inherited actual-treatment labels to subject-level ADSL context.
    subject_context = adsl[["STUDYID", "USUBJID", "TRT01P", "TRT01A", "RANDFL"]].copy()
    subject_context = subject_context.rename(columns={"TRT01A": "TRT01A_ADSL"})
    adqs_ctx = adqs.merge(subject_context, on=["STUDYID", "USUBJID"], how="left", validate="many_to_one")
    actual_label_mismatch = adqs_ctx["TRT01A_ADSL"].notna() & (adqs_ctx["TRT01A"].astype(str) != adqs_ctx["TRT01A_ADSL"].astype(str))
    _check(
        checks,
        "ADQS inherited actual-treatment labels reconcile to ADSL actual treatment",
        not actual_label_mismatch.any(),
        f"mismatched_rows={int(actual_label_mismatch.sum())}",
    )

    adsl_mi = adsl.copy()
    adsl_mi["TRT01A_ACTUAL"] = adsl_mi["TRT01A"]
    rand_mask = adsl_mi["RANDFL"].astype(str).eq("Y")
    adsl_mi.loc[rand_mask, "TRT01A"] = adsl_mi.loc[rand_mask, "TRT01P"]
    adsl_mi["MI_ASSIGNMENT_SOURCE"] = "TRT01P"

    adqs_mi = adqs_ctx.copy()
    adqs_mi["TRT01A_ACTUAL"] = adqs_mi["TRT01A"]
    adqs_rand_mask = adqs_mi["RANDFL"].astype(str).eq("Y")
    adqs_mi.loc[adqs_rand_mask, "TRT01A"] = adqs_mi.loc[adqs_rand_mask, "TRT01P"]
    adqs_mi["MI_ASSIGNMENT_SOURCE"] = "TRT01P"
    adqs_mi = adqs_mi.drop(columns=["TRT01A_ADSL"])

    mi_rand = adsl_mi.loc[adsl_mi["RANDFL"].astype(str).eq("Y")]
    remapped_counts = {arm: int((mi_rand["TRT01A"].astype(str) == arm).sum()) for arm in cfg["required_arms"]}
    actual_context_preserved = bool((adsl_mi.loc[rand_mask, "TRT01A_ACTUAL"].astype(str).values == adsl.loc[rand_mask, "TRT01A"].astype(str).values).all())
    _check(
        checks,
        "MI input uses planned assignment while preserving actual-treatment context",
        remapped_counts == expected_counts and actual_context_preserved,
        f"mi_counts={remapped_counts}; actual_context_preserved={actual_context_preserved}",
    )

    target = rand.loc[rand["USUBJID"].astype(str).isin(baseline_rand)].copy()
    pair_counts = {
        "LOW_VS_PLACEBO": int(target["TRT01P"].isin(["Placebo", "Xanomeline Low Dose"]).sum()),
        "HIGH_VS_PLACEBO": int(target["TRT01P"].isin(["Placebo", "Xanomeline High Dose"]).sum()),
    }
    pair_expected = int(cfg["expected_pairwise_mi_target_n"])
    _check(
        checks,
        "planned-assignment pairwise MI target counts reconcile before imputation",
        set(pair_counts.values()) == {pair_expected},
        f"pair_targets={pair_counts}",
    )

    visits = {"Week 8", "Week 16", "Week 24"}
    observed_by_visit = {
        visit: set(mmrm.loc[mmrm["AVISIT"].astype(str).eq(visit), "USUBJID"].astype(str))
        for visit in visits
    }
    week24_obs = len(observed_by_visit["Week 24"])
    week24_missing = len(rand_ids) - week24_obs
    _check(
        checks,
        "Week 24 observed/missing denominator reconciles to the randomised population",
        week24_obs == int(cfg["expected_week24_observed"]) and week24_missing == int(cfg["expected_week24_missing"]),
        f"observed={week24_obs}; missing={week24_missing}; randomised={len(rand_ids)}",
    )

    provenance = adsl[["STUDYID", "USUBJID", "TRT01P", "TRT01A", "RANDFL", "SAFFL"]].copy()
    provenance["ASSIGNMENT_MISMATCH"] = provenance["TRT01P"].astype(str) != provenance["TRT01A"].astype(str)
    provenance["ACTOT_BASELINE_AVAILABLE"] = provenance["USUBJID"].astype(str).isin(baseline_ids)
    provenance["PRIMARY_MMRM_INCLUDED"] = provenance["USUBJID"].astype(str).isin(mmrm_ids)
    for visit in sorted(visits):
        col = visit.upper().replace(" ", "") + "_OBSERVED"
        provenance[col] = provenance["USUBJID"].astype(str).isin(observed_by_visit[visit])
    provenance["WEEK24_MISSING"] = provenance["RANDFL"].astype(str).eq("Y") & ~provenance["WEEK24_OBSERVED"]
    provenance["POPULATION_STATUS"] = "NOT_RANDOMISED"
    randomized_rows = provenance["RANDFL"].astype(str).eq("Y")
    provenance.loc[randomized_rows & ~provenance["ACTOT_BASELINE_AVAILABLE"], "POPULATION_STATUS"] = "RANDOMISED_NO_BASELINE_ACTOT"
    provenance.loc[randomized_rows & provenance["ACTOT_BASELINE_AVAILABLE"] & ~provenance["PRIMARY_MMRM_INCLUDED"], "POPULATION_STATUS"] = "RANDOMISED_BASELINE_NO_OBSERVED_POSTBASELINE"
    provenance.loc[randomized_rows & provenance["PRIMARY_MMRM_INCLUDED"], "POPULATION_STATUS"] = "PRIMARY_MMRM_INCLUDED"

    adsl_mi.to_csv(outputs / "adsl_mi_planned.csv", index=False)
    adqs_mi.to_csv(outputs / "adqs_actot_mi_planned.csv", index=False)
    provenance.to_csv(outputs / "analysis_population_provenance.csv", index=False)
    pd.DataFrame(checks).to_csv(outputs / "mi_assignment_input_checks.csv", index=False)

    all_passed = all(bool(x["passed"]) for x in checks)
    metrics = {
        "analysis_version": VERSION,
        "assignment_claim": cfg["assignment_claim"],
        "subjects": int(len(adsl)),
        "randomised_subjects": int(len(rand)),
        "randomised_planned_counts": planned_counts_norm,
        "randomised_actual_counts": {arm: int(actual_counts.get(arm, 0)) for arm in cfg["required_arms"]},
        "assignment_mismatches": int(len(mismatch)),
        "mismatch_primary_mmrm_subjects": int(len(mismatch_mmrm)),
        "baseline_randomised_subjects": int(len(baseline_rand)),
        "primary_mmrm_subjects": int(len(mmrm_ids)),
        "randomised_baseline_no_observed_postbaseline": int(len(baseline_rand.difference(mmrm_ids))),
        "week24_observed": int(week24_obs),
        "week24_missing": int(week24_missing),
        "pairwise_mi_target_counts": pair_counts,
        "required_checks": len(checks),
        "required_checks_passed": sum(bool(x["passed"]) for x in checks),
        "all_passed": all_passed,
    }
    (outputs / "mi_assignment_input_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    status_counts = provenance["POPULATION_STATUS"].value_counts().to_dict()
    lines = [
        "# v0.23 randomised-treatment assignment and population provenance",
        "",
        f"Input gate: **{'PASS' if all_passed else 'FAIL'}**",
        f"Controlled claim: `{cfg['assignment_claim']}`",
        "",
        f"- Subjects: **{len(adsl)}**; randomised: **{len(rand)}**.",
        f"- Planned randomised counts: **{planned_counts_norm}**.",
        f"- Actual-treatment counts among randomised subjects: **{{arm: int(actual_counts.get(arm, 0)) for arm in cfg['required_arms']}}**.",
        f"- Planned/actual mismatches: **{len(mismatch)}**; current primary-MMRM mismatches: **{len(mismatch_mmrm)}**.",
        f"- Randomised baseline ACTOT: **{len(baseline_rand)}**; primary MMRM subjects: **{len(mmrm_ids)}**.",
        f"- Randomised baseline subjects with no observed Week 8/16/24 ACTOT: **{len(baseline_rand.difference(mmrm_ids))}**.",
        f"- Week 24 observed/missing: **{week24_obs}/{week24_missing}**.",
        f"- Planned-assignment pairwise MI target counts: **{pair_counts}**.",
        f"- Population-status counts: **{status_counts}**.",
        "",
        "MI-specific copies preserve the original actual-treatment value in `TRT01A_ACTUAL` while using planned randomised assignment as the grouping value in `TRT01A` for the existing rbmi programs.",
        "",
        "## Evidence boundary",
        "",
        str(cfg["evidence_boundary"]),
        "",
    ]
    (outputs / "mi_assignment_input_summary.md").write_text("\n".join(lines), encoding="utf-8")

    if not all_passed:
        raise ValueError("v0.23 MI assignment input gate failed; inspect outputs/mi_assignment_input_checks.csv")
    return metrics


def assess_mi_assignment_outputs(root: Path) -> dict[str, Any]:
    root = Path(root)
    cfg = _load_json(root / "spec" / "mi_assignment_v0_23.json")
    _validate_cfg(cfg)
    outputs = root / "outputs"
    input_metrics = _load_json(outputs / "mi_assignment_input_metrics.json")
    pair_counts = pd.read_csv(outputs / "rbmi_pairwise_input_counts.csv")
    ref = pd.read_csv(outputs / "table22_rbmi_reference_based.csv")
    checks: list[dict[str, Any]] = []

    _check(
        checks,
        "v0.23 planned-assignment input gate passed before MI execution",
        bool(input_metrics.get("all_passed")),
        f"input_all_passed={input_metrics.get('all_passed')}",
    )
    expected = int(cfg["expected_pairwise_mi_target_n"])
    pair_target = pair_counts.groupby("comparison_id")["target_n"].nunique().to_dict()
    pair_values = pair_counts.groupby("comparison_id")["target_n"].first().astype(int).to_dict()
    pair_ok = set(pair_values) == {"LOW_VS_PLACEBO", "HIGH_VS_PLACEBO"} and all(v == expected for v in pair_values.values()) and all(v == 1 for v in pair_target.values())
    _check(
        checks,
        "executed rbmi pairwise target counts use the planned randomised allocation",
        pair_ok,
        f"executed_pair_targets={pair_values}",
    )

    strategies = set(ref["strategy_id"].astype(str))
    comparisons = set(ref["comparison_id"].astype(str))
    ref_ok = len(ref) == 8 and strategies == {"MAR", "JR", "CR", "CIR"} and comparisons == {"LOW_VS_PLACEBO", "HIGH_VS_PLACEBO"}
    _check(
        checks,
        "reference-based MI retains the complete controlled sensitivity set after assignment repair",
        ref_ok,
        f"rows={len(ref)}; strategies={sorted(strategies)}; comparisons={sorted(comparisons)}",
    )
    if "mcse_pass" in ref.columns:
        mcse = ref["mcse_pass"].astype(str).str.lower().eq("true") if ref["mcse_pass"].dtype != bool else ref["mcse_pass"]
        _check(checks, "reference-based MI Monte Carlo precision remains acceptable after assignment repair", bool(mcse.all()), f"mcse_pass={int(mcse.sum())}/{len(mcse)}")

    all_passed = all(bool(x["passed"]) for x in checks)
    metrics = {
        "analysis_version": VERSION,
        "assignment_claim": cfg["assignment_claim"],
        "executed_pairwise_mi_target_counts": pair_values,
        "reference_based_rows": int(len(ref)),
        "required_checks": len(checks),
        "required_checks_passed": sum(bool(x["passed"]) for x in checks),
        "all_passed": all_passed,
    }
    pd.DataFrame(checks).to_csv(outputs / "mi_assignment_output_checks.csv", index=False)
    (outputs / "mi_assignment_output_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# v0.23 executed MI assignment audit",
        "",
        f"Post-MI gate: **{'PASS' if all_passed else 'FAIL'}**",
        f"Controlled claim: `{cfg['assignment_claim']}`",
        f"Executed pairwise target counts: **{pair_values}**.",
        f"Reference-based rows: **{len(ref)}**.",
        "",
        str(cfg["evidence_boundary"]),
        "",
    ]
    (outputs / "mi_assignment_output_summary.md").write_text("\n".join(lines), encoding="utf-8")
    if not all_passed:
        raise ValueError("v0.23 executed MI assignment audit failed; inspect outputs/mi_assignment_output_checks.csv")
    return metrics
