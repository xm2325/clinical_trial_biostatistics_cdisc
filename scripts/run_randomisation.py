from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.randomisation import generate_randomisation_schedule


SPEC_PATH = ROOT / "spec" / "randomisation_schedule.json"
OUTPUT_DIR = ROOT / "outputs"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    spec_bytes = SPEC_PATH.read_bytes()
    spec = json.loads(spec_bytes.decode("utf-8"))
    result = generate_randomisation_schedule(spec)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "unblinded": OUTPUT_DIR / "randomisation_schedule_unblinded.csv",
        "blinded": OUTPUT_DIR / "randomisation_schedule_blinded.csv",
        "kit_code_list": OUTPUT_DIR / "kit_code_list_unblinded.csv",
        "balance": OUTPUT_DIR / "randomisation_balance.csv",
        "block_summary": OUTPUT_DIR / "randomisation_block_summary.csv",
        "qc": OUTPUT_DIR / "randomisation_qc.csv",
        "metrics": OUTPUT_DIR / "randomisation_metrics.json",
        "summary": OUTPUT_DIR / "randomisation_summary.md",
    }

    result.unblinded.to_csv(paths["unblinded"], index=False)
    result.blinded.to_csv(paths["blinded"], index=False)
    result.kit_code_list.to_csv(paths["kit_code_list"], index=False)
    result.balance.to_csv(paths["balance"], index=False)
    result.block_summary.to_csv(paths["block_summary"], index=False)
    result.qc.to_csv(paths["qc"], index=False)

    required = result.qc.loc[result.qc["required"]]
    all_passed = bool(required["passed"].all())
    arm_counts = result.unblinded.groupby("treatment").size().to_dict()
    block_size_counts = (
        result.unblinded[["block_id", "block_size"]]
        .drop_duplicates()["block_size"]
        .value_counts()
        .sort_index()
        .to_dict()
    )

    metrics = {
        "analysis_version": spec["analysis_version"],
        "randomisation_spec_sha256": hashlib.sha256(spec_bytes).hexdigest(),
        "random_seed": int(spec["random_seed"]),
        "planned_total_randomised": int(spec["design_link"]["planned_total_randomised"]),
        "generated_randomisations": int(len(result.unblinded)),
        "generated_kits": int(len(result.kit_code_list)),
        "strata": int(result.unblinded["stratum"].nunique()),
        "blocks": int(result.unblinded["block_id"].nunique()),
        "arm_counts": {str(k): int(v) for k, v in arm_counts.items()},
        "block_size_counts": {str(k): int(v) for k, v in block_size_counts.items()},
        "required_qc_passed": int(required["passed"].sum()),
        "required_qc_checks": int(len(required)),
        "all_required_qc_passed": all_passed,
    }
    paths["metrics"].write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

    # Hash generated schedules only after all CSVs have been written.
    output_hashes = {
        key: _sha256(path)
        for key, path in paths.items()
        if key in {"unblinded", "blinded", "kit_code_list", "balance", "block_summary", "qc"}
    }

    lines = [
        "# Randomisation and initial-kit schedule summary",
        "",
        f"- Version: {spec['analysis_version']}.",
        f"- Status: {spec['schedule_status']}",
        f"- Linked planning scenario: {spec['design_link']['protocol_design_scenario']} ({metrics['planned_total_randomised']} planned randomisations).",
        f"- Method: {spec['allocation']['method']}; allocation ratio 1:1:1; allowed block sizes {spec['allocation']['allowed_block_sizes']}.",
        f"- Generated: {metrics['generated_randomisations']} randomisation numbers, {metrics['generated_kits']} initial kit codes, {metrics['strata']} strata and {metrics['blocks']} permuted blocks.",
        f"- Treatment counts: {metrics['arm_counts']}.",
        f"- Required schedule QC: {metrics['required_qc_passed']}/{metrics['required_qc_checks']} passed.",
        "",
        "## Access-boundary outputs",
        "",
        "- `randomisation_schedule_blinded.csv`: randomisation ID, stratum and kit ID only.",
        "- `randomisation_schedule_unblinded.csv`: includes treatment, blind code and block information.",
        "- `kit_code_list_unblinded.csv`: kit-to-treatment decoding list.",
        "",
        "In a real blinded trial, the seed, block structure and unblinded treatment/kit code lists would be access-controlled and would not be exposed in a public repository.",
        "",
        "## Generated-output SHA256",
        "",
    ]
    for key, digest in output_hashes.items():
        lines.append(f"- {key}: `{digest}`")
    lines.extend(["", spec["kit_scope"], ""])
    paths["summary"].write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(metrics, indent=2))
    print(paths["summary"].read_text(encoding="utf-8"))
    if not all_passed:
        raise SystemExit("Required randomisation/kit schedule QC failed")


if __name__ == "__main__":
    main()
