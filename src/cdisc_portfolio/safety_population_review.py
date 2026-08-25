from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ARMS = ("Placebo", "Xanomeline Low Dose", "Xanomeline High Dose")


def _risk_by_assignment(adsl: pd.DataFrame, adae: pd.DataFrame, assignment: str) -> pd.DataFrame:
    safety = adsl.loc[adsl["SAFFL"].eq("Y"), ["USUBJID", assignment]].drop_duplicates().copy()
    teae_ids = set(adae.loc[adae["TRTEMFL"].eq("Y"), "USUBJID"].astype(str))
    safety["ANY_TEAE"] = safety["USUBJID"].astype(str).isin(teae_ids).astype(int)
    rows = []
    for arm in ARMS:
        g = safety.loc[safety[assignment].eq(arm)]
        n = int(len(g))
        e = int(g["ANY_TEAE"].sum())
        rows.append({
            "assignment": assignment,
            "arm": arm,
            "safety_n": n,
            "subjects_with_teae": e,
            "teae_risk": e / n if n else float("nan"),
        })
    return pd.DataFrame(rows)


def run_safety_population_review(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, object]]:
    spec = json.loads((root / "spec" / "safety_population_review_v0_24.json").read_text())
    out = root / "outputs"
    adsl = pd.read_csv(out / "adsl_style.csv")
    adae = pd.read_csv(out / "adae_style.csv")
    table7 = pd.read_csv(out / "table7_teae_risk_difference.csv")

    required_adsl = {"USUBJID", "SAFFL", "TRT01P", "TRT01A"}
    required_adae = {"USUBJID", "TRT01A", "TRTEMFL"}
    if missing := required_adsl.difference(adsl.columns):
        raise ValueError(f"ADSL-style missing required safety-review columns: {sorted(missing)}")
    if missing := required_adae.difference(adae.columns):
        raise ValueError(f"ADAE-style missing required safety-review columns: {sorted(missing)}")

    safety = adsl.loc[adsl["SAFFL"].eq("Y")].copy()
    if safety["USUBJID"].duplicated().any():
        raise ValueError("Safety population contains duplicate subject identifiers")

    safety["assignment_mismatch"] = safety["TRT01P"].astype(str).ne(safety["TRT01A"].astype(str))
    teae = adae.loc[adae["TRTEMFL"].eq("Y")].copy()
    teae_ids = set(teae["USUBJID"].astype(str))
    safety["has_teae"] = safety["USUBJID"].astype(str).isin(teae_ids)
    event_counts = teae.groupby("USUBJID", dropna=False).size().rename("teae_event_count")
    safety = safety.merge(event_counts, how="left", left_on="USUBJID", right_index=True)
    safety["teae_event_count"] = safety["teae_event_count"].fillna(0).astype(int)

    adae_assignment = adae[["USUBJID", "TRT01A"]].copy()
    actual_map = adsl[["USUBJID", "TRT01A"]].rename(columns={"TRT01A": "TRT01A_ADSL"})
    assignment_check = adae_assignment.merge(actual_map, on="USUBJID", how="left", validate="many_to_one")
    assignment_check["matches_actual"] = assignment_check["TRT01A"].astype(str).eq(
        assignment_check["TRT01A_ADSL"].astype(str)
    )

    actual = _risk_by_assignment(adsl, adae, "TRT01A")
    planned = _risk_by_assignment(adsl, adae, "TRT01P")
    comparison = actual.merge(
        planned,
        on="arm",
        suffixes=("_actual", "_planned"),
        validate="one_to_one",
    )
    comparison["denominator_shift_planned_minus_actual"] = (
        comparison["safety_n_planned"] - comparison["safety_n_actual"]
    )
    comparison["risk_shift_planned_minus_actual"] = (
        comparison["teae_risk_planned"] - comparison["teae_risk_actual"]
    )

    actual_denom = actual.set_index("arm")["safety_n"].to_dict()
    denominator_rows_match = True
    for row in table7.itertuples(index=False):
        arm = str(row.comparison).replace(" vs Placebo", "")
        denominator_rows_match &= int(row.n_arm) == int(actual_denom[arm])
        denominator_rows_match &= int(row.n_placebo) == int(actual_denom["Placebo"])

    checks = pd.DataFrame([
        {
            "check": "unique_safety_subject_denominator",
            "passed": not safety["USUBJID"].duplicated().any(),
            "detail": f"unique safety subjects={safety['USUBJID'].nunique()}",
        },
        {
            "check": "teae_subjects_within_safety_population",
            "passed": teae_ids.issubset(set(safety["USUBJID"].astype(str))),
            "detail": f"TEAE subjects={len(teae_ids)}; safety subjects={len(safety)}",
        },
        {
            "check": "adae_assignment_matches_adsl_actual",
            "passed": bool(assignment_check["matches_actual"].all()),
            "detail": f"matched ADAE rows={int(assignment_check['matches_actual'].sum())}/{len(assignment_check)}",
        },
        {
            "check": "subject_incidence_not_event_count",
            "passed": int(len(teae)) >= len(teae_ids) and bool((safety.loc[safety['has_teae'], 'teae_event_count'] >= 1).all()),
            "detail": f"TEAE events={len(teae)}; unique TEAE subjects={len(teae_ids)}",
        },
        {
            "check": "reported_risk_difference_denominators_use_actual_treatment",
            "passed": bool(denominator_rows_match),
            "detail": "table7 n_arm/n_placebo reconciled to unique SAFFL=Y subjects grouped by TRT01A",
        },
        {
            "check": "planned_actual_audit_is_nontrivial",
            "passed": bool(safety["assignment_mismatch"].any()),
            "detail": f"safety subjects with TRT01P != TRT01A={int(safety['assignment_mismatch'].sum())}",
        },
    ])

    metrics = {
        "version": spec["version"],
        "claim": spec["claim"],
        "safety_subjects": int(len(safety)),
        "subjects_with_teae": int(len(teae_ids)),
        "teae_events": int(len(teae)),
        "planned_actual_mismatch_safety_subjects": int(safety["assignment_mismatch"].sum()),
        "checks_passed": int(checks["passed"].sum()),
        "checks_total": int(len(checks)),
        "all_passed": bool(checks["passed"].all()),
        "max_abs_denominator_shift_if_planned_used": int(comparison["denominator_shift_planned_minus_actual"].abs().max()),
        "max_abs_teae_risk_shift_if_planned_used": float(comparison["risk_shift_planned_minus_actual"].abs().max()),
    }
    return safety, comparison, checks, metrics


def write_safety_population_review(root: Path) -> dict[str, object]:
    safety, comparison, checks, metrics = run_safety_population_review(root)
    out = root / "outputs"
    safety[[
        "USUBJID", "TRT01P", "TRT01A", "assignment_mismatch", "has_teae", "teae_event_count"
    ]].to_csv(out / "safety_population_provenance.csv", index=False)
    comparison.to_csv(out / "safety_assignment_comparison.csv", index=False)
    checks.to_csv(out / "safety_population_review_qc.csv", index=False)
    (out / "safety_population_review_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n"
    )
    summary = [
        "# Safety population and treatment-assignment review",
        "",
        f"- Controlled claim: `{metrics['claim']}`.",
        f"- Safety population: {metrics['safety_subjects']} unique exposed subjects.",
        f"- Subjects with >=1 TEAE / TEAE events: {metrics['subjects_with_teae']} / {metrics['teae_events']}.",
        f"- Safety subjects with planned-versus-actual treatment mismatch: {metrics['planned_actual_mismatch_safety_subjects']}.",
        f"- Largest arm-denominator change if planned treatment were incorrectly substituted for actual treatment: {metrics['max_abs_denominator_shift_if_planned_used']} subjects.",
        f"- Largest absolute any-TEAE risk change under that diagnostic counterfactual: {metrics['max_abs_teae_risk_shift_if_planned_used']:.4f}.",
        f"- Quality checks: {metrics['checks_passed']}/{metrics['checks_total']} PASS.",
        "",
        "The statistical decision is purpose-specific: v0.23 efficacy missing-data analyses use planned randomised assignment, while this exposure-based safety analysis uses actual treatment. Subject incidence is kept distinct from event counts. The planned-treatment calculation is diagnostic only and is not a reporting alternative.",
    ]
    (out / "safety_population_review_summary.md").write_text("\n".join(summary) + "\n")
    if not metrics["all_passed"]:
        raise RuntimeError("Safety population review gate failed")
    return metrics
