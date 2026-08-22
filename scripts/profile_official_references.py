from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.derive import derive_adsl_style  # noqa: E402
from cdisc_portfolio.efficacy import derive_adqscibc_style  # noqa: E402
from cdisc_portfolio.io import (  # noqa: E402
    ensure_inputs,
    ensure_official_json_inputs,
    read_dataset_json,
    read_sdtm,
)
from cdisc_portfolio.reference import (  # noqa: E402
    compare_adqscibc_reference,
    profile_adqsadas_reference,
    trace_adqscibc_value_mismatches,
)


def main() -> None:
    cache = ROOT / "cache"
    outputs = ROOT / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)

    inputs = ensure_inputs(cache)
    official = ensure_official_json_inputs(cache)

    dm = read_sdtm(inputs["dm"])
    ex = read_sdtm(inputs["ex"])
    ds = read_sdtm(inputs["ds"])
    qs = read_dataset_json(official["qs"])
    adqscibc_ref = read_dataset_json(official["adqscibc_reference"])
    adqsadas_ref = read_dataset_json(official["adqsadas_reference"])

    adsl = derive_adsl_style(dm, ex, ds)
    adqscibc = derive_adqscibc_style(qs, adsl)
    metrics, detail = compare_adqscibc_reference(adqscibc, adqscibc_ref)
    trace = trace_adqscibc_value_mismatches(qs, detail)

    profile, params, visits, samples = profile_adqsadas_reference(adqsadas_ref)
    (outputs / "adqsadas_reference_profile.json").write_text(
        json.dumps(profile, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    params.to_csv(outputs / "adqsadas_param_counts.csv", index=False)
    visits.to_csv(outputs / "adqsadas_visit_counts.csv", index=False)
    samples.to_csv(outputs / "adqsadas_samples.csv", index=False)
    trace.to_csv(outputs / "adqscibc_mismatch_source_trace.csv", index=False)

    actot_ref = adqsadas_ref.loc[
        adqsadas_ref["PARAMCD"].fillna("").astype(str).str.upper().eq("ACTOT")
    ].copy()
    actot_ref.to_csv(outputs / "adqsadas_actot_reference.csv", index=False)
    actot_group_cols = [
        c for c in ["AVISIT", "AVISITN", "DTYPE", "EFFFL", "ANL01FL", "ABLFL"]
        if c in actot_ref.columns
    ]
    actot_counts = (
        actot_ref.groupby(actot_group_cols, dropna=False).size().reset_index(name="records")
        .sort_values([c for c in ["AVISITN", "DTYPE", "EFFFL", "ANL01FL"] if c in actot_group_cols])
    )
    actot_counts.to_csv(outputs / "adqsadas_actot_reference_counts.csv", index=False)

    print("--- official ADQSADAS profile ---")
    print(json.dumps(profile, indent=2, sort_keys=True))
    print("--- official ADQSADAS parameter counts ---")
    print(params.to_csv(index=False))
    print("--- official ACTOT row semantics ---")
    print(actot_counts.to_csv(index=False))
    print("--- CIBIC reference mismatches traced to official QS ---")
    if trace.empty:
        print("none")
    else:
        display = [
            c for c in [
                "USUBJID", "AVISIT", "QSSEQ_DER", "QSTESTCD", "QSORRES",
                "QSSTRESC", "QSSTRESN", "AVAL_DER", "AVAL_REF",
                "DERIVED_EQUALS_SOURCE", "REFERENCE_EQUALS_SOURCE",
            ] if c in trace.columns
        ]
        print(trace[display].to_csv(index=False))


if __name__ == "__main__":
    main()
