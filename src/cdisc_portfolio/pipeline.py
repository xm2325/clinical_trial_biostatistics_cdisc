from __future__ import annotations

import json
from pathlib import Path

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
from .io import SOURCE_URLS, ensure_inputs, read_sdtm, sha256_file
from .qc import run_qc
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

    tables = {
        "table1_demographics": demographics_summary(adsl),
        "table2_disposition": disposition_summary(adsl),
        "table3_exposure": exposure_summary(adsl),
        "table4_teae_overview": teae_overview(adsl, adae),
        "table5_teae_soc_pt": teae_by_soc_pt(adsl, adae),
        "table6_teae_severity": teae_by_severity(adsl, adae),
        "table7_teae_risk_difference": teae_risk_differences(adsl, adae),
    }

    out_paths: dict[str, Path] = {
        "adsl_style": output_dir / "adsl_style.csv",
        "adae_style": output_dir / "adae_style.csv",
    }
    adsl.to_csv(out_paths["adsl_style"], index=False)
    adae.to_csv(out_paths["adae_style"], index=False)
    for name, table in tables.items():
        path = output_dir / f"{name}.csv"
        table.to_csv(path, index=False)
        out_paths[name] = path

    qc = run_qc(adsl, adae)
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
    metrics = {
        "input_rows": {"DM": int(len(dm)), "AE": int(len(ae)), "DS": int(len(ds)), "EX": int(len(ex))},
        "randomized_subjects": randomized_n,
        "safety_subjects": safety_n,
        "completed_subjects": completed_n,
        "subjects_with_teae": teae_subject_n,
        "teae_events": teae_event_n,
        "exposure_end_fallback_subjects": exposure_end_fallback_n,
        "ds_exposure_end_fallback_subjects": ds_exposure_end_fallback_n,
        "required_qc_checks": int(len(required_qc)),
        "required_qc_passed": int(required_qc["passed"].sum()),
        "qc_all_passed": qc_all_passed,
    }
    metrics_path = output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out_paths["metrics"] = metrics_path

    manifest = {
        "source_urls": SOURCE_URLS,
        "inputs_sha256": {name: sha256_file(path) for name, path in inputs.items()},
        "outputs_sha256": {name: sha256_file(path) for name, path in out_paths.items()},
        "qc_all_passed": qc_all_passed,
        "analysis_version": "0.2.0",
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    note = (
        "# Analysis run note\n\n"
        f"- Input rows: DM={len(dm)}, AE={len(ae)}, DS={len(ds)}, EX={len(ex)}.\n"
        f"- Randomised subjects: {randomized_n}.\n"
        f"- Safety population (>=1 EX record): {safety_n}.\n"
        f"- Completed subjects: {completed_n}.\n"
        f"- Subjects with >=1 portfolio-defined TEAE: {teae_subject_n}.\n"
        f"- Portfolio-defined TEAE events: {teae_event_n}.\n"
        f"- Exposure-end fallback subjects: {exposure_end_fallback_n} (DS disposition fallback: {ds_exposure_end_fallback_n}).\n"
        f"- Required QC checks passed: {metrics['required_qc_passed']}/{metrics['required_qc_checks']}.\n"
        f"- QC all required checks passed: {qc_all_passed}.\n\n"
        "The TEAE rule and inferential comparisons are pre-specified portfolio assumptions, not claims about the original pilot protocol or a regulatory submission.\n"
    )
    (output_dir / "analysis_run_note.md").write_text(note, encoding="utf-8")
    return metrics
