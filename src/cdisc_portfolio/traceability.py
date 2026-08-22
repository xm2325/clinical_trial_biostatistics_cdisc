from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


REGISTRY_COLUMNS = [
    "tlf_id",
    "registry_version",
    "title",
    "objective",
    "population",
    "endpoint",
    "method",
    "source_domains",
    "analysis_dataset",
    "output_file",
    "qc_evidence",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _split_paths(value: object) -> list[str]:
    return [x.strip() for x in str(value).split("|") if x.strip()]


def validate_traceability(
    root: Path,
    registry_path: Path | None = None,
    contracts_path: Path | None = None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Validate planned TLF rows against generated analysis artifacts."""
    root = Path(root)
    registry_path = registry_path or root / "spec" / "analysis_traceability.csv"
    contracts_path = contracts_path or root / "spec" / "output_contracts.json"

    registry = pd.read_csv(registry_path, dtype=str, keep_default_na=False)
    missing_registry_columns = [c for c in REGISTRY_COLUMNS if c not in registry.columns]
    if missing_registry_columns:
        raise ValueError(f"Traceability registry missing columns: {missing_registry_columns}")
    if registry.empty:
        raise ValueError("Traceability registry is empty")
    if registry["tlf_id"].duplicated().any():
        dup = registry.loc[registry["tlf_id"].duplicated(keep=False), "tlf_id"].tolist()
        raise ValueError(f"Duplicate TLF IDs: {sorted(set(dup))}")

    versions = sorted({x.strip() for x in registry["registry_version"].astype(str) if x.strip()})
    if len(versions) != 1 or not bool(registry["registry_version"].astype(str).str.strip().ne("").all()):
        raise ValueError(f"Traceability registry must declare one non-empty registry_version; found={versions}")
    registry_version = versions[0]

    metadata_complete = registry[REGISTRY_COLUMNS].apply(lambda s: s.astype(str).str.strip().ne("")).all(axis=1)
    if not bool(metadata_complete.all()):
        bad = registry.loc[~metadata_complete, "tlf_id"].tolist()
        raise ValueError(f"Traceability metadata incomplete for: {bad}")

    contracts = json.loads(contracts_path.read_text(encoding="utf-8"))
    registry_ids = set(registry["tlf_id"])
    contract_ids = set(contracts)
    if registry_ids != contract_ids:
        missing = sorted(registry_ids - contract_ids)
        extra = sorted(contract_ids - registry_ids)
        raise ValueError(f"Registry/contract ID mismatch; missing contracts={missing}; extra contracts={extra}")

    rows: list[dict[str, object]] = []
    for rec in registry.to_dict(orient="records"):
        tlf_id = rec["tlf_id"]
        contract = contracts[tlf_id]
        contract_output = str(contract.get("output_file", ""))
        output_matches_registry = contract_output == rec["output_file"]
        output_path = root / rec["output_file"]
        output_exists = output_path.is_file()

        required_columns = [str(x) for x in contract.get("required_columns", [])]
        min_rows = int(contract.get("min_rows", 1))
        row_count = 0
        missing_columns: list[str] = required_columns.copy()
        output_sha256 = ""
        read_error = ""

        if output_exists:
            try:
                out = pd.read_csv(output_path)
                row_count = int(len(out))
                missing_columns = sorted(set(required_columns) - set(map(str, out.columns)))
                output_sha256 = _sha256(output_path)
            except Exception as exc:
                read_error = f"{type(exc).__name__}: {exc}"

        required_columns_ok = output_exists and not missing_columns and not read_error
        row_count_ok = output_exists and not read_error and row_count >= min_rows

        analysis_paths = _split_paths(rec["analysis_dataset"])
        analysis_dataset_exists = bool(analysis_paths) and all((root / p).is_file() for p in analysis_paths)
        missing_analysis_datasets = [p for p in analysis_paths if not (root / p).is_file()]

        qc_paths = _split_paths(rec["qc_evidence"])
        qc_evidence_exists = bool(qc_paths) and all((root / p).is_file() for p in qc_paths)
        missing_qc_evidence = [p for p in qc_paths if not (root / p).is_file()]

        passed = all([
            output_matches_registry,
            output_exists,
            required_columns_ok,
            row_count_ok,
            analysis_dataset_exists,
            qc_evidence_exists,
        ])
        rows.append({
            "tlf_id": tlf_id,
            "registry_version": rec["registry_version"],
            "title": rec["title"],
            "output_file": rec["output_file"],
            "output_matches_contract": output_matches_registry,
            "output_exists": output_exists,
            "row_count": row_count,
            "min_rows": min_rows,
            "row_count_ok": row_count_ok,
            "required_columns_ok": required_columns_ok,
            "missing_columns": "|".join(missing_columns),
            "analysis_dataset_exists": analysis_dataset_exists,
            "missing_analysis_datasets": "|".join(missing_analysis_datasets),
            "qc_evidence_exists": qc_evidence_exists,
            "missing_qc_evidence": "|".join(missing_qc_evidence),
            "output_sha256": output_sha256,
            "read_error": read_error,
            "passed": passed,
        })

    detail = pd.DataFrame(rows)
    metrics: dict[str, object] = {
        "analysis_version": registry_version,
        "planned_tlfs": int(len(detail)),
        "passed_tlfs": int(detail["passed"].sum()),
        "outputs_found": int(detail["output_exists"].sum()),
        "output_contracts_passed": int((detail["required_columns_ok"] & detail["row_count_ok"]).sum()),
        "analysis_dataset_links_resolved": int(detail["analysis_dataset_exists"].sum()),
        "qc_evidence_links_resolved": int(detail["qc_evidence_exists"].sum()),
        "all_passed": bool(detail["passed"].all()),
    }
    return detail, metrics


def write_traceability_outputs(root: Path) -> dict[str, object]:
    root = Path(root)
    detail, metrics = validate_traceability(root)
    output_dir = root / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    detail.to_csv(output_dir / "traceability_validation.csv", index=False)
    (output_dir / "traceability_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# SAP-to-TLF traceability validation",
        "",
        f"- Registry version: {metrics['analysis_version']}.",
        f"- Planned TLFs: {metrics['planned_tlfs']}.",
        f"- TLFs passing complete structural traceability: {metrics['passed_tlfs']}/{metrics['planned_tlfs']}.",
        f"- Output files found: {metrics['outputs_found']}/{metrics['planned_tlfs']}.",
        f"- Output contracts passed: {metrics['output_contracts_passed']}/{metrics['planned_tlfs']}.",
        f"- Analysis-dataset links resolved: {metrics['analysis_dataset_links_resolved']}/{metrics['planned_tlfs']}.",
        f"- QC-evidence links resolved: {metrics['qc_evidence_links_resolved']}/{metrics['planned_tlfs']}.",
        "",
        "This structural gate supplements, rather than replaces, analysis-specific statistical QC.",
    ]
    (output_dir / "traceability_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return metrics
