"""Runtime-efficient v0.7 runner.

The scientific model is defined in ``v07_phq9_anchor_purification``. This runner
reuses the common background model within each nine-item DIF screen. For a
current background set B, items outside B use B as the common null and B+{j}
as the alternative; items already in B use B-{j} as the null and B as the
common alternative. The nested 4-df LRT is unchanged while repeated equivalent
optimisations are removed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd
from scipy.stats import chi2

import v07_phq9_anchor_purification as core


def dif_screen_cached(
    x,
    weights,
    group,
    pooled_raw,
    background_free_items: Iterable[int] = (),
    maxiter: int = 140,
) -> pd.DataFrame:
    background = set(int(i) for i in background_free_items)
    background_model = core.fit_multigroup_free_items(
        x,
        weights,
        group,
        pooled_raw,
        free_items=background,
        maxiter=maxiter,
    )

    rows = []
    for item_index, item_name in enumerate(core.ITEMS):
        if item_index in background:
            null_free = background - {item_index}
            null_model = core.fit_multigroup_free_items(
                x,
                weights,
                group,
                background_model["shared_raw"],
                free_items=null_free,
                maxiter=maxiter,
                initial_latent_mean=background_model["comparison_latent_mean"],
                initial_latent_sd=background_model["comparison_latent_sd"],
            )
            alternative = background_model
        else:
            null_free = background
            null_model = background_model
            alternative_free = background | {item_index}
            alternative = core.fit_multigroup_free_items(
                x,
                weights,
                group,
                background_model["shared_raw"],
                free_items=alternative_free,
                maxiter=maxiter,
                initial_latent_mean=background_model["comparison_latent_mean"],
                initial_latent_sd=background_model["comparison_latent_sd"],
            )

        statistic = max(
            0.0, 2.0 * (alternative["loglik"] - null_model["loglik"])
        )
        rows.append(
            {
                "item": item_name,
                "item_index": item_index,
                "background_free_items": ",".join(
                    core.ITEMS[i] for i in sorted(null_free)
                ),
                "n_anchor_items_in_null": len(core.ITEMS) - len(null_free),
                "null_loglik": null_model["loglik"],
                "alternative_loglik": alternative["loglik"],
                "lrt_chi2_df4": statistic,
                "p_value": float(chi2.sf(statistic, 4)),
                "null_fit_success": null_model["success"],
                "alternative_fit_success": alternative["success"],
            }
        )

    result = pd.DataFrame(rows)
    result["q_value_bh"] = core.bh_fdr(result["p_value"].to_numpy())
    result["dif_flag_fdr_0_05"] = result["q_value_bh"] < 0.05
    return result


def merge_design_audit_into_summary(argv: list[str]) -> None:
    if "--out" not in argv:
        raise ValueError("v0.7 runner requires --out so design metadata can be merged")
    outdir = Path(argv[argv.index("--out") + 1])
    summary_path = outdir / "v07_anchor_purification_summary.json"
    design_path = outdir / "v07_design_structure_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(summary_path)
    if not design_path.exists():
        raise FileNotFoundError(
            f"{design_path} is required; run v07_nhanes_design_audit.py first"
        )

    summary = json.loads(summary_path.read_text())
    design = json.loads(design_path.read_text())
    if design.get("complete_case_domain_n") != summary.get("cohort_n"):
        raise ValueError(
            "NHANES design audit domain does not match the v0.7 psychometric cohort"
        )
    summary["nhanes_design_structure"] = design
    summary_path.write_text(json.dumps(summary, indent=2))


# All higher-level v0.7 routines resolve dif_screen from the core module at run
# time, so this substitution changes only redundant optimisation, not the model.
core.dif_screen = dif_screen_cached


if __name__ == "__main__":
    core.main()
    merge_design_audit_into_summary(sys.argv)
