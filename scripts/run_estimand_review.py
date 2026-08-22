from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.estimand import derive_actot_missingness, review_estimand_consistency  # noqa: E402
from cdisc_portfolio.io import sha256_file  # noqa: E402

OUTPUT_DIR = ROOT / "outputs"
SPEC_PATH = ROOT / "spec" / "estimands.json"


def main() -> None:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    adsl = pd.read_csv(OUTPUT_DIR / "adsl_style.csv")
    adqs = pd.read_csv(OUTPUT_DIR / "adqs_actot_style.csv")
    mmrm = pd.read_csv(OUTPUT_DIR / "mmrm_analysis_dataset.csv")

    missingness, patterns, reasons = derive_actot_missingness(adsl, adqs)
    missingness.to_csv(OUTPUT_DIR / "table16_actot_missingness_by_visit.csv", index=False)
    patterns.to_csv(OUTPUT_DIR / "actot_missingness_patterns.csv", index=False)
    reasons.to_csv(OUTPUT_DIR / "table17_week24_missingness_by_disposition.csv", index=False)

    review = review_estimand_consistency(spec, adsl, adqs, mmrm, missingness, reasons)
    review.to_csv(OUTPUT_DIR / "estimand_review.csv", index=False)
    required = review.loc[review["required"].eq(True)].copy()
    all_passed = bool(len(required) > 0 and required["passed"].all())

    wk24 = missingness.loc[missingness["AVISIT"].eq("Week 24")].copy()
    metrics = {
        "analysis_version": "0.11.0",
        "estimand_id": spec["estimands"][0]["id"],
        "target_population": int(missingness.groupby("TRT01A")["target_n"].first().sum()),
        "week24_observed": int(wk24["observed_n"].sum()),
        "week24_missing": int(wk24["missing_n"].sum()),
        "week24_missing_pct": float(100.0 * wk24["missing_n"].sum() / wk24["target_n"].sum()),
        "observed_after_discontinuation_records": int(missingness["observed_after_discontinuation_n"].sum()),
        "required_checks": int(len(required)),
        "required_passed": int(required["passed"].sum()),
        "all_required_passed": all_passed,
        "estimand_spec_sha256": sha256_file(SPEC_PATH),
    }
    (OUTPUT_DIR / "estimand_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# ACTOT estimand and missing-data review",
        "",
        "- Version: 0.11.0.",
        f"- Estimand: {metrics['estimand_id']}.",
        "- Intercurrent event: treatment discontinuation; strategy: treatment policy.",
        "- Primary estimator: observed-data REML MMRM; no LOCF rows enter the primary model.",
        "- Missing post-baseline measurements are handled under the model's MAR assumption; the descriptive missingness tables do not assert MAR.",
        f"- Portfolio target population: {metrics['target_population']} randomised subjects with observed baseline ACTOT.",
        f"- Week 24: observed={metrics['week24_observed']}; missing={metrics['week24_missing']} ({metrics['week24_missing_pct']:.1f}%).",
        f"- Observed post-discontinuation arm-visit records retained in the treatment-policy review: {metrics['observed_after_discontinuation_records']}.",
        f"- Required estimand/missing-data checks: {metrics['required_passed']}/{metrics['required_checks']} passed.",
        "",
        "The existing Week 24 LOCF ANCOVA is retained only as a supportive legacy-style stress test. It is not the primary estimator and is not used to define the treatment-policy estimand.",
        "",
        "This is an independent portfolio review, not a sponsor-approved estimand, missing-data strategy or regulatory analysis decision.",
    ]
    (OUTPUT_DIR / "estimand_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(metrics, indent=2, sort_keys=True))
    print((OUTPUT_DIR / "estimand_summary.md").read_text(encoding="utf-8"))
    if not all_passed:
        failed = required.loc[~required["passed"]]
        print(failed.to_string(index=False))
        raise SystemExit("Required estimand/missing-data review checks failed")


if __name__ == "__main__":
    main()
