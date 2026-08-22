from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.mnar_sensitivity import run_delta_sensitivity


def main() -> None:
    out = ROOT / "outputs"
    out.mkdir(parents=True, exist_ok=True)

    spec = json.loads((ROOT / "spec" / "mnar_sensitivity.json").read_text(encoding="utf-8"))
    contrasts = pd.read_csv(out / "mmrm_treatment_contrasts.csv")
    missingness = pd.read_csv(out / "table16_actot_missingness_by_visit.csv")

    grid, tipping, qc, metrics, summary = run_delta_sensitivity(spec, contrasts, missingness)

    # Always retain the gate evidence first. If an input/QC failure returns an
    # empty analysis grid, these files remain available in the CI artifact for
    # investigation rather than being masked by a downstream dataframe error.
    qc.to_csv(out / "mnar_sensitivity_qc.csv", index=False)
    (out / "mnar_sensitivity_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    (out / "mnar_sensitivity_summary.md").write_text(summary, encoding="utf-8")
    print(summary)

    if not metrics["all_required_passed"]:
        raise SystemExit("MNAR sensitivity gate failed; inspect outputs/mnar_sensitivity_qc.csv")

    input_columns = [
        "scenario_id",
        "comparison",
        "active_arm",
        "placebo_missing_prop",
        "active_missing_prop",
        "active_multiplier",
        "placebo_multiplier",
        "contrast_shift_per_delta",
        "primary_estimate",
        "SE_fixed_delta",
        "df",
    ]
    sensitivity_inputs = (
        grid.loc[grid["delta"].eq(0.0), input_columns]
        .sort_values(["scenario_id", "comparison"])
        .reset_index(drop=True)
    )

    sensitivity_inputs.to_csv(out / "mnar_sensitivity_inputs.csv", index=False)
    grid.to_csv(out / "table18_actot_delta_sensitivity.csv", index=False)
    tipping.to_csv(out / "table19_actot_directional_tipping_points.csv", index=False)


if __name__ == "__main__":
    main()
