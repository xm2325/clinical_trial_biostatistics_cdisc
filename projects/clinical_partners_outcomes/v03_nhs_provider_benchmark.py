from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from v03_nhs_schema_audit import read_csv_flex

PERCENTAGE_MEASURES = [
    "Percentage_AccessingServices6WeeksFinishedCourseTreatment",
    "Percentage_AccessingServices18WeeksFinishedCourseTreatment",
    "Percentage_ReliableDeterioration",
    "Percentage_ReliableImprovement",
    "Percentage_Recovery",
    "Percentage_ReliableRecovery",
]
COUNT_MEASURES = [
    "Count_ReferralsReceived",
    "Count_AccessingServices",
    "Count_EndedReferrals",
    "Count_FinishedCourseTreatment",
    "Count_ReliableDeterioration",
]
HIGHER_IS_BETTER = {
    "Percentage_AccessingServices6WeeksFinishedCourseTreatment": True,
    "Percentage_AccessingServices18WeeksFinishedCourseTreatment": True,
    "Percentage_ReliableDeterioration": False,
    "Percentage_ReliableImprovement": True,
    "Percentage_Recovery": True,
    "Percentage_ReliableRecovery": True,
}


def clean_nhs(df: pd.DataFrame) -> pd.DataFrame:
    required = {
        "REPORTING_PERIOD_START", "GROUP_TYPE", "ORG_CODE2", "ORG_NAME2",
        "MEASURE_ID", "MEASURE_NAME", "MEASURE_VALUE",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise KeyError(f"NHS time series missing expected columns: {missing}")
    out = df.copy()
    out["reporting_month"] = pd.to_datetime(out["REPORTING_PERIOD_START"], errors="raise")
    out["value"] = pd.to_numeric(out["MEASURE_VALUE"].replace("*", np.nan), errors="coerce")
    out["suppressed_or_non_numeric"] = out["value"].isna()
    return out


def provider_panel(df: pd.DataFrame) -> pd.DataFrame:
    panel = df[df["GROUP_TYPE"].eq("Provider")].copy()
    panel = panel[panel["MEASURE_NAME"].isin(PERCENTAGE_MEASURES + COUNT_MEASURES)].copy()
    # In the provider roll-up, ORG_CODE2 / ORG_NAME2 is the provider identity.
    panel = panel.rename(columns={"ORG_CODE2": "provider_code", "ORG_NAME2": "provider_name"})
    if panel.duplicated(["reporting_month", "provider_code", "MEASURE_NAME"]).any():
        dupes = panel[panel.duplicated(["reporting_month", "provider_code", "MEASURE_NAME"], keep=False)]
        raise AssertionError(f"Provider roll-up is not unique at month/provider/measure: {len(dupes)} rows")
    return panel


def england_series(df: pd.DataFrame) -> pd.DataFrame:
    eng = df[df["GROUP_TYPE"].eq("England") & df["MEASURE_NAME"].isin(PERCENTAGE_MEASURES + COUNT_MEASURES)].copy()
    if eng.duplicated(["reporting_month", "MEASURE_NAME"]).any():
        raise AssertionError("England aggregate is not unique by month/measure")
    return eng[["reporting_month", "MEASURE_ID", "MEASURE_NAME", "value"]].sort_values(["MEASURE_NAME", "reporting_month"])


def latest_distribution(panel: pd.DataFrame, england: pd.DataFrame, outdir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    latest_month = panel["reporting_month"].max()
    latest = panel[panel["reporting_month"].eq(latest_month)].copy()
    dist_rows = []
    rank_rows = []
    for measure in PERCENTAGE_MEASURES:
        g = latest[latest["MEASURE_NAME"].eq(measure) & latest["value"].notna()].copy()
        if g.empty:
            continue
        eng_match = england[(england["reporting_month"].eq(latest_month)) & england["MEASURE_NAME"].eq(measure)]
        eng_value = float(eng_match["value"].iloc[0]) if len(eng_match) else float("nan")
        dist_rows.append({
            "reporting_month": latest_month.date().isoformat(),
            "measure": measure,
            "n_providers_observed": int(len(g)),
            "n_providers_suppressed_or_missing": int((latest["MEASURE_NAME"].eq(measure)).sum() - len(g)),
            "provider_mean": float(g["value"].mean()),
            "provider_sd": float(g["value"].std()),
            "provider_p10": float(g["value"].quantile(0.10)),
            "provider_p25": float(g["value"].quantile(0.25)),
            "provider_median": float(g["value"].median()),
            "provider_p75": float(g["value"].quantile(0.75)),
            "provider_p90": float(g["value"].quantile(0.90)),
            "england_aggregate": eng_value,
            "higher_is_better": HIGHER_IS_BETTER[measure],
        })
        pct = g["value"].rank(method="average", pct=True)
        if not HIGHER_IS_BETTER[measure]:
            pct = 1.0 - pct + (1.0 / len(g))
        temp = g[["provider_code", "provider_name", "value"]].copy()
        temp["measure"] = measure
        temp["reporting_month"] = latest_month.date().isoformat()
        temp["favourable_percentile"] = pct.to_numpy()
        temp["england_aggregate"] = eng_value
        temp["difference_from_england"] = temp["value"] - eng_value
        rank_rows.append(temp)
    dist = pd.DataFrame(dist_rows)
    ranks = pd.concat(rank_rows, ignore_index=True) if rank_rows else pd.DataFrame()
    dist.to_csv(outdir / "nhs_provider_latest_distribution.csv", index=False)
    ranks.to_csv(outdir / "nhs_provider_latest_percentiles.csv", index=False)
    return dist, ranks


def year_over_year(panel: pd.DataFrame, outdir: Path) -> pd.DataFrame:
    latest_month = panel["reporting_month"].max()
    earliest_month = panel["reporting_month"].min()
    target = panel[
        panel["reporting_month"].isin([earliest_month, latest_month])
        & panel["MEASURE_NAME"].isin(PERCENTAGE_MEASURES)
        & panel["value"].notna()
    ].copy()
    wide = target.pivot_table(
        index=["provider_code", "provider_name", "MEASURE_NAME"],
        columns="reporting_month", values="value", aggfunc="first"
    ).reset_index()
    if earliest_month not in wide.columns or latest_month not in wide.columns:
        return pd.DataFrame()
    wide = wide.rename(columns={earliest_month: "value_first_month", latest_month: "value_latest_month"})
    wide = wide.dropna(subset=["value_first_month", "value_latest_month"]).copy()
    wide["absolute_change"] = wide["value_latest_month"] - wide["value_first_month"]
    wide["first_month"] = earliest_month.date().isoformat()
    wide["latest_month"] = latest_month.date().isoformat()
    wide.to_csv(outdir / "nhs_provider_first_to_latest_change.csv", index=False)
    return wide


def ecological_associations(panel: pd.DataFrame, outdir: Path) -> pd.DataFrame:
    latest_month = panel["reporting_month"].max()
    latest = panel[panel["reporting_month"].eq(latest_month) & panel["value"].notna()].copy()
    wide = latest.pivot_table(index=["provider_code", "provider_name"], columns="MEASURE_NAME", values="value", aggfunc="first").reset_index()
    pairs = [
        ("Percentage_AccessingServices6WeeksFinishedCourseTreatment", "Percentage_ReliableImprovement"),
        ("Percentage_AccessingServices6WeeksFinishedCourseTreatment", "Percentage_ReliableRecovery"),
        ("Percentage_AccessingServices6WeeksFinishedCourseTreatment", "Percentage_ReliableDeterioration"),
        ("Percentage_ReliableImprovement", "Percentage_ReliableRecovery"),
    ]
    rows = []
    for x, y in pairs:
        if x not in wide.columns or y not in wide.columns:
            continue
        g = wide[[x, y]].dropna()
        rows.append({
            "reporting_month": latest_month.date().isoformat(),
            "x_measure": x,
            "y_measure": y,
            "n_providers": int(len(g)),
            "spearman_rho": float(g[x].corr(g[y], method="spearman")) if len(g) >= 3 else float("nan"),
            "interpretation_boundary": "Provider-level ecological association only; not a patient-level or causal effect.",
        })
    result = pd.DataFrame(rows)
    result.to_csv(outdir / "nhs_provider_ecological_associations.csv", index=False)
    return result


def save_provider_plot(dist: pd.DataFrame, outdir: Path) -> None:
    if dist.empty:
        return
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    labels = [x.replace("Percentage_", "").replace("FinishedCourseTreatment", "") for x in dist["measure"]]
    y = np.arange(len(dist))
    med = dist["provider_median"].to_numpy()
    lo = med - dist["provider_p25"].to_numpy()
    hi = dist["provider_p75"].to_numpy() - med
    ax.errorbar(med, y, xerr=np.vstack([lo, hi]), fmt="o", capsize=3, label="Provider median and IQR")
    ax.scatter(dist["england_aggregate"], y, marker="x", s=55, label="England aggregate")
    ax.set_yticks(y, labels)
    ax.set_xlabel("Percentage")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(outdir / "nhs_provider_latest_benchmark.png", dpi=220)
    plt.close(fig)


def main(path: Path, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    df = clean_nhs(read_csv_flex(path))
    panel = provider_panel(df)
    england = england_series(df)
    england.to_csv(outdir / "nhs_england_key_measure_time_series.csv", index=False)
    panel[["reporting_month", "provider_code", "provider_name", "MEASURE_ID", "MEASURE_NAME", "value", "suppressed_or_non_numeric"]].to_csv(
        outdir / "nhs_provider_key_measure_panel.csv", index=False
    )
    dist, ranks = latest_distribution(panel, england, outdir)
    yoy = year_over_year(panel, outdir)
    assoc = ecological_associations(panel, outdir)
    save_provider_plot(dist, outdir)

    latest_month = panel["reporting_month"].max()
    earliest_month = panel["reporting_month"].min()
    summary = {
        "source_rows": int(len(df)),
        "provider_panel_rows": int(len(panel)),
        "provider_count_any_month": int(panel["provider_code"].nunique()),
        "first_month": earliest_month.date().isoformat(),
        "latest_month": latest_month.date().isoformat(),
        "latest_percentage_measures_benchmarked": int(len(dist)),
        "latest_provider_rank_rows": int(len(ranks)),
        "first_to_latest_change_rows": int(len(yoy)),
        "ecological_associations_reported": int(len(assoc)),
        "measures_used": PERCENTAGE_MEASURES + COUNT_MEASURES,
        "excluded_measure_warning": "M351 mean days waited between treatments is not present in this key-measures file and is not used; NHS England has warned against using M351 in the current publication series.",
        "interpretation_boundary": (
            "Provider distributions and changes are published aggregate service statistics. They are useful for benchmarking and hypothesis generation, but they do not adjust for patient case mix and cannot identify patient-level treatment or waiting-time effects."
        ),
    }
    (outdir / "nhs_provider_benchmark_summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    print("NHS_PROVIDER_BENCHMARK_SUMMARY:", json.dumps(summary))
    print("NHS_PROVIDER_LATEST_DISTRIBUTION:\n", dist.to_string(index=False))
    print("NHS_PROVIDER_ECOLOGICAL_ASSOCIATIONS:\n", assoc.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    main(args.data, args.out)
