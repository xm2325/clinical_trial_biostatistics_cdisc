from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _validate_ae(frame: pd.DataFrame, subject_ids: set[str]) -> list[dict[str, object]]:
    key = ["STUDYID", "USUBJID", "AESEQ"]
    required_columns = {"STUDYID", "USUBJID", "AESEQ", "ASTDT", "TRTEMFL"}
    duplicate_keys = int(frame.duplicated(key).sum()) if set(key).issubset(frame.columns) else len(frame)
    unknown_subjects = int((~frame["USUBJID"].astype(str).isin(subject_ids)).sum()) if "USUBJID" in frame else len(frame)
    parsed_dates = pd.to_datetime(frame.get("ASTDT", pd.Series(dtype=object)), errors="coerce")
    nonblank_dates = frame.get("ASTDT", pd.Series(dtype=object)).fillna("").astype(str).str.strip().ne("")
    malformed_dates = int((nonblank_dates & parsed_dates.isna()).sum())
    schema_missing = sorted(required_columns.difference(frame.columns))
    bad_te = sorted(set(frame.get("TRTEMFL", pd.Series(dtype=object)).fillna("").astype(str).str.strip()) - {"", "Y"})
    return [
        {"check": "required_columns_present", "passed": not schema_missing, "detail": f"missing={schema_missing}"},
        {"check": "ae_key_unique", "passed": duplicate_keys == 0, "detail": f"duplicate_keys={duplicate_keys}"},
        {"check": "subjects_known_to_adsl", "passed": unknown_subjects == 0, "detail": f"unknown_subject_rows={unknown_subjects}"},
        {"check": "astdt_parseable_when_present", "passed": malformed_dates == 0, "detail": f"malformed_dates={malformed_dates}"},
        {"check": "trtemfl_y_blank_contract", "passed": not bad_te, "detail": f"invalid_values={bad_te}"},
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clinical-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    clinical = Path(args.clinical_dir)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    adsl_path = next(clinical.rglob("adsl_style.csv"), None)
    adae_path = next(clinical.rglob("adae_style.csv"), None)
    if adsl_path is None or adae_path is None:
        raise SystemExit("Controlled ADSL/ADAE outputs not found for transfer-QC evidence")

    adsl = pd.read_csv(adsl_path, keep_default_na=False)
    adae = pd.read_csv(adae_path, keep_default_na=False)
    subject_ids = set(adsl["USUBJID"].astype(str))

    # Version 1 intentionally injects three representative receipt defects. It is a deterministic
    # public-data portfolio fixture, not a claim about an actual external vendor transfer.
    v1 = adae.copy()
    v1 = pd.concat([v1, v1.iloc[[0]].copy()], ignore_index=True)
    if len(v1) >= 3:
        v1.loc[1, "USUBJID"] = "PORTFOLIO-UNKNOWN-SUBJECT"
        v1.loc[2, "ASTDT"] = "2026-99-99"
    v1_path = out / "vendor_ae_transfer_v1_rejected.csv"
    v1.to_csv(v1_path, index=False)

    # Version 2 is the corrected controlled transfer and must release without suppressing checks.
    v2 = adae.copy()
    v2_path = out / "vendor_ae_transfer_v2_released.csv"
    v2.to_csv(v2_path, index=False)

    rows: list[dict[str, object]] = []
    decisions: dict[str, str] = {}
    for version, path, frame in [("v1", v1_path, v1), ("v2", v2_path, v2)]:
        checks = _validate_ae(frame, subject_ids)
        all_pass = all(bool(check["passed"]) for check in checks)
        decision = "RELEASE" if all_pass else "REJECT_AND_QUARANTINE"
        decisions[version] = decision
        for check in checks:
            rows.append({"transfer_version": version, **check, "required": True, "release_decision": decision})
        rows.append({
            "transfer_version": version,
            "check": "file_identity_sha256",
            "passed": True,
            "detail": _sha256(path),
            "required": False,
            "release_decision": decision,
        })

    qc = pd.DataFrame(rows)
    qc.to_csv(out / "vendor_transfer_qc.csv", index=False)
    expected_behaviour = decisions.get("v1") == "REJECT_AND_QUARANTINE" and decisions.get("v2") == "RELEASE"
    metrics = {
        "version": "0.28.0",
        "fixture_type": "deterministic public-data vendor-transfer simulation",
        "v1_decision": decisions.get("v1"),
        "v2_decision": decisions.get("v2"),
        "reject_then_release_passed": expected_behaviour,
        "controlled_claim": "PORTFOLIO_VENDOR_TRANSFER_RECEIPT_GATE_RECONCILED" if expected_behaviour else None,
        "evidence_boundary": "Synthetic transfer-control evidence derived from public portfolio data; not an actual sponsor/CRO/vendor transfer or validated GxP data-management process.",
    }
    (out / "vendor_transfer_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = (
        "# Vendor transfer receipt and release decision\n\n"
        f"- Incoming v1: **{decisions.get('v1')}** after deliberate duplicate-key, unknown-subject and malformed-date defects.\n"
        f"- Corrected v2: **{decisions.get('v2')}** under the same unsuppressed checks.\n"
        f"- Reject-then-release contract: **{expected_behaviour}**.\n\n"
        "Evidence boundary: this is a deterministic public-data portfolio fixture, not an actual vendor transfer or GxP process.\n"
    )
    (out / "vendor_transfer_release_decision.md").write_text(summary, encoding="utf-8")
    print(json.dumps(metrics, indent=2, sort_keys=True))
    if not expected_behaviour:
        raise SystemExit("Vendor-transfer receipt/release evidence gate failed")


if __name__ == "__main__":
    main()
