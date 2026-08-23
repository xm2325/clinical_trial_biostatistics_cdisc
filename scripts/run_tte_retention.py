from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.tte import derive_retention_adtte


SPEC_PATH = ROOT / "spec" / "tte_retention.json"
ADSL_PATH = ROOT / "outputs" / "adsl_style.csv"
OUT = ROOT / "outputs"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if not ADSL_PATH.exists():
        raise FileNotFoundError(f"Missing ADSL-style input: {ADSL_PATH}")
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    adsl = pd.read_csv(ADSL_PATH)
    result = derive_retention_adtte(adsl, spec)

    OUT.mkdir(parents=True, exist_ok=True)
    dataset_path = OUT / "adtte_retention_style.csv"
    qc_path = OUT / "adtte_retention_qc.csv"
    metrics_path = OUT / "adtte_retention_metrics.json"
    summary_path = OUT / "adtte_retention_summary.md"

    result.dataset.to_csv(dataset_path, index=False)
    result.qc.to_csv(qc_path, index=False)
    metrics = dict(result.metrics)
    metrics["spec_sha256"] = sha256(SPEC_PATH)
    metrics["adsl_source_sha256"] = sha256(ADSL_PATH)
    metrics["adtte_output_sha256"] = sha256(dataset_path)
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# ADTTE-style retention derivation summary",
        "",
        "- Endpoint: exploratory time from first treatment date to study discontinuation.",
        "- Discontinuation (`DCSFL=Y`) is the event (`CNSR=0`).",
        "- Protocol completion (`COMPLFL=Y`) is censored at `EOSDT` (`CNSR=1`).",
        "- Duration: `AVAL = ADT - STARTDT + 1` days.",
        f"- Subjects: {metrics['subjects']}; events: {metrics['events']}; censored: {metrics['censored']}.",
        f"- Required derivation QC: {metrics['required_passed']}/{metrics['required_checks']} passed.",
        "",
        "## By treatment arm",
        "",
        "| Arm | Subjects | Events | Censored |",
        "|---|---:|---:|---:|",
    ]
    for arm, counts in metrics["arm_counts"].items():
        lines.append(
            f"| {arm} | {counts['subjects']} | {counts['events']} | {counts['censored']} |"
        )
    lines.extend(
        [
            "",
            "This is an ADTTE-style BDS portfolio exercise using public data. It is not claimed to be a formal submission-ready ADaM dataset or sponsor-approved endpoint.",
        ]
    )
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if not metrics["all_required_passed"]:
        failed = result.qc[(result.qc["required"]) & (~result.qc["passed"])]
        raise SystemExit("ADTTE retention derivation QC failed: " + "; ".join(failed["check"].tolist()))


if __name__ == "__main__":
    main()
