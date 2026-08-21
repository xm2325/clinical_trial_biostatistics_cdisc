from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .analysis import (
    demographics_summary,
    disposition_summary,
    exposure_summary,
    teae_by_severity,
    teae_by_soc_pt,
    teae_overview,
    teae_risk_differences,
)
from .derive import derive_adae_style, derive_adsl_style
from .efficacy import (
    acitm01_descriptive,
    acitm01_week24_ancova,
    derive_acitm01_adqs_style,
    derive_adqscibc_style,
)
from .efficacy_qc import run_efficacy_qc
from .io import (
    OFFICIAL_JSON_URLS,
    SOURCE_URLS,
    ensure_inputs,
    ensure_official_json_inputs,
    read_dataset_json,
    read_sdtm,
    sha256_file,
)
from .qc import run_qc
from .reference import compare_adqscibc_reference
from .sample_size import two_arm_binary_n_per_arm, two_arm_continuous_n_per_arm


def run(root: Path) -> dict[str, object]:
    cache_dir = root / "cache"
    output_dir = root / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    inputs = ensure_inputs(cache_dir)
    dm = read_sdtm(inputs["dm"])
    ae = read_sdtm(inputs["ae"])
    ds = read_sdtm(inputs["ds"])
    ex = read_sdtm(inputs["ex"])

    adsl = derive_adsl_style(dm, ex, ds)
    adae = derive_adae_style(ae, adsl, followup_days=30)

    safety_tables = {
        "table1_demographics": demographics_summary(adsl),
        "table2_disposition": disposition_summary(adsl),
        "table3_exposure": exposure_summary(adsl),
        "table4_teae_overview": teae_overview(adsl, adae),
        "table5_teae_soc_pt": teae_by_soc_pt(adsl, adae),
        "table6_teae_severity": teae_by_severity(adsl, adae),
        "table7_teae_risk_difference": teae_risk_differences(adsl, adae),
    }

    official_inputs = ensure_official_json_inputs(cache_dir)
    qs = read_dataset_json(official_inputs["qs"])
    adqscibc_reference = read_dataset_json(official_inputs["adqscibc_reference"])

    adqscibc = derive_adqscibc_style(qs, adsl)
    adqs_acitm01 = derive_acitm01_adqs_style(qs, adsl)
    efficacy_descriptive = acitm01_descriptive(adqs_acitm01)
    efficacy_lsmeans, efficacy_contrasts, ancova_subjects = acitm01_week24_ancova(adqs_acitm01)
    reference_metrics, reference_detail = compare_adqscibc_reference(adqscibc, adqscibc_reference)

    out_paths: dict[str, Path] = {
        "adsl_style": output_dir / "adsl_style.csv",
        "adae_style": output_dir / "adae_style.csv",
        "adqscibc_style": output_dir / "adqscibc_style.csv",
        "adqs_acitm01_style": output_dir / "adqs_acitm01_style.csv",
        "ancova_analysis_subjects": output_dir / "ancova_analysis_subjects.csv",
        "adqscibc_reference_metrics": output_dir / "adqscibc_reference_metrics.csv",
        "adqscibc_reference_detail": output_dir / "adqscibc_reference_detail.csv",
    }
    adsl.to_csv(out_paths["adsl_style"], index=False)
    adae.to_csv(out_paths["adae_style"], index=False)
    adqscibc.to_csv(out_paths["adqscibc_style"], index=False)
    adqs_acitm01.to_csv(out_paths["adqs_acitm01_style"], index=False)
    ancova_subjects.to_csv(out_paths["ancova_analysis_subjects"], index=False)
    reference_metrics.to_csv(out_paths["adqscibc_reference_metrics"], index=False)
    reference_detail.to_csv(out_paths["adqscibc_reference_detail"], index=False)

    all_tables = {
        **safety_tables,
        "table8_acitm01_descriptive": efficacy_descriptive,
        "table9_acitm01_lsmeans": efficacy_lsmeans,
        "table10_acitm01_ancova_contrasts": efficacy_contrasts,
    }
    for name, table in all_tables.items():
        path = output_dir / f"{name}.csv"
        table.to_csv(path, index=False)
        out_paths[name] = path

    safety_qc = run_qc(adsl, adae).assign(area="safety")
    efficacy_qc = run_efficacy_qc(adqscibc, adqs_acitm01, reference_metrics, ancova_subjects).assign(area="efficacy")
    qc = pd.concat([safety_qc, efficacy_qc], ignore_index=True)
    qc_path = output_dir / "qc_report.csv"
    qc.to_csv(qc_path, index=False)
    out_paths["qc"] = qc_path

    sample_sizes = {
        "continuous_example_n_per_arm": two_arm_continuous_n_per_arm(effect=3.0, sd=10.0, power=0.90),
        "binary_example_n_per_arm": two_arm_binary_n_per_arm(p_control=0.30, p_treatment=0.20, power=0.90),
    }
    sample_path = output_dir / "sample_size_examples.json"
    sample_path.write_text(json.dumps(sample_sizes, indent=2) + "\n", encoding="utf-8")
    out_paths["sample_sizes"] = sample_path

    required_qc = qc.loc[qc["required"].eq(True)]
    qc_all_passed = bool(required_qc["passed"].all())
    safety_n = int(adsl["SAFFL"].eq("Y").sum())
    randomized_n = int(adsl["RANDFL"].eq("Y").sum())
    completed_n = int((adsl["RANDFL"].eq("Y") & adsl["COMPLFL"].eq("Y")).sum())
    teae_subject_n = int(adae.loc[adae["TRTEMFL"].eq("Y"), "USUBJID"].nunique())
    teae_event_n = int(adae["TRTEMFL"].eq("Y").sum())
    exposure_end_fallback_n = int(adsl.loc[adsl["SAFFL"].eq("Y"), "TRTEDTSRC"].ne("EX").sum())
    ds_exposure_end_fallback_n = int(adsl.loc[adsl["SAFFL"].eq("Y"), "TRTEDTSRC"].eq("DS_DISPOSITION_FALLBACK").sum())

    ref = reference_metrics.iloc[0]
    obs_n = int(ancova_subjects.loc[ancova_subjects["analysis"].eq("Observed Week 24"), "USUBJID"].nunique())
    locf_n = int(ancova_subjects.loc[ancova_subjects["analysis"].eq("LOCF sensitivity"), "USUBJID"].nunique())
    metrics = {
        "input_rows": {
            "DM": int(len(dm)), "AE": int(len(ae)), "DS": int(len(ds)), "EX": int(len(ex)),
            "QS_official": int(len(qs)), "ADQSCIBC_reference": int(len(adqscibc_reference)),
        },
        "randomized_subjects": randomized_n,
        "safety_subjects": safety_n,
        "completed_subjects": completed_n,
        "subjects_with_teae": teae_subject_n,
        "teae_events": teae_event_n,
        "exposure_end_fallback_subjects": exposure_end_fallback_n,
        "ds_exposure_end_fallback_subjects": ds_exposure_end_fallback_n,
        "adqscibc_derived_rows": int(len(adqscibc)),
        "adqscibc_reference_key_coverage": float(ref["reference_key_coverage"]),
        "adqscibc_aval_match_rate": float(ref["aval_match_rate_on_overlap"]),
        "adqscibc_dtype_match_rate": float(ref["dtype_match_rate_on_overlap"]),
        "acitm01_observed_week24_subjects": obs_n,
        "acitm01_locf_subjects": locf_n,
        "required_qc_checks": int(len(required_qc)),
        "required_qc_passed": int(required_qc["passed"].sum()),
        "qc_all_passed": qc_all_passed,
    }
    metrics_path = output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out_paths["metrics"] = metrics_path

    all_input_paths = {**inputs, **official_inputs}
    manifest = {
        "source_urls": {**SOURCE_URLS, **OFFICIAL_JSON_URLS},
        "inputs_sha256": {name: sha256_file(path) for name, path in all_input_paths.items()},
        "outputs_sha256": {name: sha256_file(path) for name, path in out_paths.items()},
        "qc_all_passed": qc_all_passed,
        "analysis_version": "0.3.0",
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    note = (
        "# Analysis run note\n\n"
        f"- Safety inputs: DM={len(dm)}, AE={len(ae)}, DS={len(ds)}, EX={len(ex)} rows.\n"
        f"- Official CDISC QS Dataset-JSON: {len(qs)} rows.\n"
        f"- Official CDISC ADQSCIBC reference: {len(adqscibc_reference)} rows.\n"
        f"- Randomised subjects: {randomized_n}; safety population: {safety_n}; completed: {completed_n}.\n"
        f"- Subjects with >=1 portfolio-defined TEAE: {teae_subject_n}; TEAE events: {teae_event_n}.\n"
        f"- ADQSCIBC-style rows: {len(adqscibc)}.\n"
        f"- Official ADQSCIBC key coverage: {float(ref['reference_key_coverage']):.2%}; AVAL match on overlap: {float(ref['aval_match_rate_on_overlap']):.2%}; DTYPE match: {float(ref['dtype_match_rate_on_overlap']):.2%}.\n"
        f"- ACITM01 Week 24 ANCOVA subjects: observed={obs_n}; LOCF sensitivity={locf_n}.\n"
        f"- Required QC checks passed: {metrics['required_qc_passed']}/{metrics['required_qc_checks']}; all passed={qc_all_passed}.\n\n"
        "Safety and efficacy analyses are independent portfolio analyses. Official reference comparison is used for validation, not to claim sponsor/CRO production experience.\n"
    )
    (output_dir / "analysis_run_note.md").write_text(note, encoding="utf-8")
    return metrics
