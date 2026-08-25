from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

SPEC_COLUMNS = [
    "program_id",
    "deliverable_type",
    "deliverable",
    "source_domains",
    "analysis_inputs",
    "output_path",
    "key_columns",
    "required_columns",
    "production_programs",
    "specification_files",
    "qc_evidence",
    "qc_mode",
]
ALLOWED_DELIVERABLE_TYPES = {"analysis_dataset", "tlf"}
ALLOWED_QC_MODES = {
    "cross_language_reconstruction",
    "derivation_qc",
    "reviewer_reconciliation",
    "cross_package_reconstruction",
}
CONTROLLED_CLAIM = "PORTFOLIO_CLINICAL_PROGRAMMING_WORKFLOW_READY"


@dataclass(frozen=True)
class ClinicalProgrammingResult:
    checks: pd.DataFrame
    release_manifest: pd.DataFrame
    metrics: dict[str, Any]


def _split(value: object) -> list[str]:
    text = "" if value is None else str(value).strip()
    if not text or text.lower() == "nan":
        return []
    return [item.strip() for item in text.split(";") if item.strip()]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _as_bool(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .map({"true": True, "false": False, "1": True, "0": False, "y": True, "n": False})
        .fillna(False)
        .astype(bool)
    )


def load_programming_spec(path: Path) -> pd.DataFrame:
    spec = pd.read_csv(path, dtype=str).fillna("")
    missing = [column for column in SPEC_COLUMNS if column not in spec.columns]
    if missing:
        raise ValueError("Clinical-programming specification missing columns: " + ", ".join(missing))
    return spec[SPEC_COLUMNS].copy()


def _add_check(
    checks: list[dict[str, Any]],
    check: str,
    passed: bool,
    detail: str,
    *,
    program_id: str = "GLOBAL",
    area: str = "workflow",
    required: bool = True,
) -> None:
    checks.append(
        {
            "program_id": program_id,
            "area": area,
            "check": check,
            "passed": bool(passed),
            "required": bool(required),
            "detail": str(detail),
        }
    )


def _qc_file_passes(path: Path) -> tuple[bool, str]:
    frame = pd.read_csv(path)
    if "passed" not in frame.columns:
        return False, "missing passed column"
    passed = _as_bool(frame["passed"])
    if "required" in frame.columns:
        required = _as_bool(frame["required"])
    else:
        required = pd.Series(True, index=frame.index, dtype=bool)
    required_rows = frame.loc[required].copy()
    required_pass = passed.loc[required]
    ok = len(required_rows) > 0 and bool(required_pass.all())
    return ok, f"required={len(required_rows)}; passed={int(required_pass.sum())}"


def run_clinical_programming_workflow(
    root: Path,
    spec_path: Path | None = None,
) -> ClinicalProgrammingResult:
    root = Path(root)
    spec_path = spec_path or root / "spec" / "clinical_programming_workflow_v0_25.csv"
    spec = load_programming_spec(spec_path)
    checks: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []

    ids = spec["program_id"].astype(str).str.strip()
    _add_check(
        checks,
        "Program IDs are non-blank and unique",
        bool(ids.ne("").all() and not ids.duplicated().any()),
        f"rows={len(ids)}; unique={ids.nunique()}",
        area="specification",
    )

    invalid_types = sorted(set(spec["deliverable_type"]) - ALLOWED_DELIVERABLE_TYPES)
    _add_check(
        checks,
        "Deliverable types are controlled",
        not invalid_types,
        f"invalid={invalid_types}",
        area="specification",
    )

    invalid_modes = sorted(set(spec["qc_mode"]) - ALLOWED_QC_MODES)
    _add_check(
        checks,
        "QC modes are controlled",
        not invalid_modes,
        f"invalid={invalid_modes}",
        area="specification",
    )

    cross_language_count = int(spec["qc_mode"].eq("cross_language_reconstruction").sum())
    _add_check(
        checks,
        "At least one package has cross-language reconstruction",
        cross_language_count >= 1,
        f"packages={cross_language_count}",
        area="validation_strategy",
    )

    source_manifest_path = root / "outputs" / "manifest.json"
    source_domains_available: set[str] = set()
    if source_manifest_path.exists():
        source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
        source_domains_available = {
            str(name).strip().upper()
            for name in source_manifest.get("source_urls", {})
        }
    _add_check(
        checks,
        "Source manifest is available",
        source_manifest_path.exists(),
        str(source_manifest_path.relative_to(root)),
        area="source_provenance",
    )

    for evidence_name, evidence_rel in [
        ("Statistical change-control gate passed", "outputs/change_impact_metrics.json"),
        ("SAP-to-TLF traceability gate passed", "outputs/traceability_metrics.json"),
    ]:
        evidence_path = root / evidence_rel
        evidence_ok = False
        detail = evidence_rel
        if evidence_path.is_file():
            payload = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence_ok = bool(payload.get("all_passed", False))
            detail = f"{evidence_rel}; all_passed={payload.get('all_passed')}"
        _add_check(
            checks,
            evidence_name,
            evidence_ok,
            detail,
            area="controlled_release",
        )

    for row in spec.to_dict(orient="records"):
        program_id = str(row["program_id"]).strip()
        deliverable = str(row["deliverable"]).strip()
        output_rel = str(row["output_path"]).strip()
        output_path = root / output_rel

        production_programs = _split(row["production_programs"])
        specification_files = _split(row["specification_files"])
        qc_evidence = _split(row["qc_evidence"])
        source_domains = [value.upper() for value in _split(row["source_domains"])]
        analysis_inputs = _split(row["analysis_inputs"])
        key_columns = _split(row["key_columns"])
        required_columns = _split(row["required_columns"])

        _add_check(
            checks,
            "Production program files exist",
            bool(production_programs) and all((root / item).is_file() for item in production_programs),
            "; ".join(production_programs),
            program_id=program_id,
            area="program_control",
        )
        _add_check(
            checks,
            "Specification files exist",
            bool(specification_files) and all((root / item).is_file() for item in specification_files),
            "; ".join(specification_files),
            program_id=program_id,
            area="specification",
        )

        if source_domains:
            missing_sources = sorted(set(source_domains) - source_domains_available)
            _add_check(
                checks,
                "Declared SDTM/source domains are present in the run manifest",
                not missing_sources,
                f"declared={source_domains}; missing={missing_sources}",
                program_id=program_id,
                area="source_provenance",
            )

        if analysis_inputs:
            missing_inputs = [item for item in analysis_inputs if not (root / item).is_file()]
            _add_check(
                checks,
                "Declared analysis inputs exist",
                not missing_inputs,
                f"declared={analysis_inputs}; missing={missing_inputs}",
                program_id=program_id,
                area="analysis_input",
            )

        _add_check(
            checks,
            "Deliverable output exists",
            output_path.is_file(),
            output_rel,
            program_id=program_id,
            area="deliverable",
        )

        output_rows: int | None = None
        output_sha256 = ""
        if output_path.is_file():
            output_sha256 = _sha256(output_path)
            if output_path.suffix.lower() == ".csv":
                output = pd.read_csv(output_path)
                output_rows = int(len(output))
                missing_columns = sorted(set(required_columns) - set(output.columns))
                _add_check(
                    checks,
                    "Required output columns are present",
                    not missing_columns,
                    f"missing={missing_columns}",
                    program_id=program_id,
                    area="dataset_contract",
                )
                if key_columns:
                    missing_keys = sorted(set(key_columns) - set(output.columns))
                    duplicate_keys = -1
                    passed = not missing_keys
                    if passed:
                        duplicate_keys = int(output.duplicated(key_columns).sum())
                        passed = duplicate_keys == 0
                    _add_check(
                        checks,
                        "Declared output key is unique",
                        passed,
                        f"keys={key_columns}; missing={missing_keys}; duplicates={duplicate_keys}",
                        program_id=program_id,
                        area="dataset_contract",
                    )

        qc_file_results: list[str] = []
        qc_files_exist = bool(qc_evidence) and all((root / item).is_file() for item in qc_evidence)
        _add_check(
            checks,
            "QC evidence files exist",
            qc_files_exist,
            "; ".join(qc_evidence),
            program_id=program_id,
            area="qc",
        )
        qc_all_pass = qc_files_exist
        if qc_files_exist:
            for item in qc_evidence:
                ok, detail = _qc_file_passes(root / item)
                qc_all_pass = qc_all_pass and ok
                qc_file_results.append(f"{item}: {detail}")
            _add_check(
                checks,
                "Required QC evidence passes",
                qc_all_pass,
                " | ".join(qc_file_results),
                program_id=program_id,
                area="qc",
            )

        manifest_rows.append(
            {
                "program_id": program_id,
                "deliverable_type": str(row["deliverable_type"]).strip(),
                "deliverable": deliverable,
                "source_domains": ";".join(source_domains),
                "analysis_inputs": ";".join(analysis_inputs),
                "analysis_input_sha256": ";".join(
                    f"{item}={_sha256(root / item)}"
                    for item in analysis_inputs
                    if (root / item).is_file()
                ),
                "output_path": output_rel,
                "output_rows": output_rows,
                "output_sha256": output_sha256,
                "production_programs": ";".join(production_programs),
                "production_program_sha256": ";".join(
                    f"{item}={_sha256(root / item)}"
                    for item in production_programs
                    if (root / item).is_file()
                ),
                "specification_files": ";".join(specification_files),
                "specification_sha256": ";".join(
                    f"{item}={_sha256(root / item)}"
                    for item in specification_files
                    if (root / item).is_file()
                ),
                "qc_mode": str(row["qc_mode"]).strip(),
                "qc_evidence": ";".join(qc_evidence),
                "qc_evidence_sha256": ";".join(
                    f"{item}={_sha256(root / item)}"
                    for item in qc_evidence
                    if (root / item).is_file()
                ),
            }
        )

    check_frame = pd.DataFrame(checks)
    required = check_frame.loc[check_frame["required"].eq(True)]
    all_required_passed = len(required) > 0 and bool(required["passed"].all())
    release_manifest = pd.DataFrame(manifest_rows)

    metrics = {
        "version": "0.25.0",
        "program_packages": int(len(spec)),
        "analysis_dataset_packages": int(spec["deliverable_type"].eq("analysis_dataset").sum()),
        "tlf_packages": int(spec["deliverable_type"].eq("tlf").sum()),
        "cross_language_packages": cross_language_count,
        "required_checks": int(len(required)),
        "required_passed": int(required["passed"].sum()),
        "all_required_passed": all_required_passed,
        "controlled_claim": CONTROLLED_CLAIM if all_required_passed else "",
        "evidence_boundary": (
            "Independent public-data portfolio evidence only; not sponsor/CRO production, "
            "formal second-programmer sign-off, formal ADaM conformance, or regulatory submission readiness."
        ),
    }
    return ClinicalProgrammingResult(
        checks=check_frame,
        release_manifest=release_manifest,
        metrics=metrics,
    )
