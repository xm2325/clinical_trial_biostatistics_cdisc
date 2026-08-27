from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from v06_phq9_psychometrics import prepare_nhanes


def audit_design(dpq_path: str | Path, demo_path: str | Path, outdir: str | Path) -> dict:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    _, cohort = prepare_nhanes(dpq_path, demo_path)
    demo = pd.read_sas(demo_path, format="xport")
    required = ["SEQN", "SDMVSTRA", "SDMVPSU", "WTMEC2YR"]
    missing = [column for column in required if column not in demo.columns]
    if missing:
        raise ValueError(f"Missing NHANES design columns: {missing}")

    design = cohort[["SEQN"]].merge(
        demo[required], on="SEQN", how="left", validate="one_to_one"
    )
    if design[["SDMVSTRA", "SDMVPSU"]].isna().any().any():
        raise ValueError("Masked variance unit fields are missing in the PHQ-9 domain")

    psu_table = (
        design.groupby(["SDMVSTRA", "SDMVPSU"], dropna=False)
        .agg(
            complete_case_n=("SEQN", "size"),
            mec_weight_sum=("WTMEC2YR", "sum"),
        )
        .reset_index()
        .sort_values(["SDMVSTRA", "SDMVPSU"])
    )
    strata_table = (
        psu_table.groupby("SDMVSTRA", as_index=False)
        .agg(
            n_masked_psu=("SDMVPSU", "nunique"),
            complete_case_n=("complete_case_n", "sum"),
            mec_weight_sum=("mec_weight_sum", "sum"),
        )
        .sort_values("SDMVSTRA")
    )

    psu_table.to_csv(outdir / "v07_design_psu_audit.csv", index=False)
    strata_table.to_csv(outdir / "v07_design_strata_audit.csv", index=False)

    n_strata = int(strata_table["SDMVSTRA"].nunique())
    n_psu = int(len(psu_table))
    summary = {
        "version": "0.7",
        "complete_case_domain_n": int(len(design)),
        "masked_strata": n_strata,
        "masked_psu": n_psu,
        "psu_minus_strata": n_psu - n_strata,
        "strata_with_one_psu_in_complete_case_domain": int(
            (strata_table["n_masked_psu"] == 1).sum()
        ),
        "strata_with_two_or_more_psu_in_complete_case_domain": int(
            (strata_table["n_masked_psu"] >= 2).sum()
        ),
        "design_fields": ["SDMVSTRA", "SDMVPSU", "WTMEC2YR"],
        "boundary": (
            "This audit confirms the public masked variance structure available "
            "for the PHQ-9 analysis domain. It does not convert the custom GRM "
            "likelihood-ratio tests into Taylor-linearised survey inference. "
            "CDC/NCHS recommends design-aware variance estimation using the "
            "masked strata, masked PSU and appropriate sampling weight, with "
            "subgroups handled as domains rather than by dropping the rest of "
            "the survey sample."
        ),
    }
    (outdir / "v07_design_structure_summary.json").write_text(
        json.dumps(summary, indent=2)
    )
    print(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dpq", required=True)
    parser.add_argument("--demo", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    audit_design(args.dpq, args.demo, args.out)


if __name__ == "__main__":
    main()
