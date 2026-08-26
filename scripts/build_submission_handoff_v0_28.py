from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

CONTROLLED_CLAIM = "PORTFOLIO_SUBMISSION_HANDOFF_PACKAGE_RECONCILED"
EVIDENCE_BOUNDARY = (
    "Submission-style public-data portfolio evidence only. The package is not an eCTD submission, not sponsor/CRO production, "
    "not a validated GxP environment, not formal ADaM conformance, and not evidence of NDA/BLA/MAA submission ownership."
)

DATASET_SOURCE_NAMES = {
    "ADSL": "adsl_style.csv",
    "ADAE": "adae_style.csv",
    "ADQS": "adqs_actot_style.csv",
    "ADTTE": "adtte_retention_style.csv",
}
SELECTED_TFLS = [
    "table7_teae_risk_difference.csv",
    "mmrm_treatment_contrasts.csv",
    "table23_actot_multiplicity.csv",
    "table24_retention_km.csv",
]
SELECTED_QC = [
    "clinical_programming_workflow_qc.csv",
    "analysis_dataset_review.csv",
    "traceability_validation.csv",
    "analysis_closure_review.csv",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _find(root: Path, name: str) -> Path:
    hit = next(root.rglob(name), None)
    if hit is None:
        raise FileNotFoundError(f"Required file {name} not found under {root}")
    return hit


def _copy_if_present(root: Path, name: str, destination: Path) -> bool:
    hit = next(root.rglob(name), None)
    if hit is None:
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(hit, destination)
    return True


def _slug(text: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "-", text.strip()).strip("-").lower()
    return value or "portfolio-study"


def _json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _make_adrg_pdf(
    path: Path,
    study_id: str,
    dataset_rows: dict[str, int],
    p21: dict[str, object],
    xpt: dict[str, object],
    target_sha: str,
) -> None:
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleTight",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=19,
        spaceAfter=8,
    )
    h1 = ParagraphStyle(
        "H1Tight",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=14,
        spaceBefore=7,
        spaceAfter=4,
    )
    body = ParagraphStyle(
        "BodyTight",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.8,
        leading=11.5,
        spaceAfter=4,
    )
    small = ParagraphStyle("Small", parent=body, fontSize=7.8, leading=10)
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )
    story = [
        Paragraph("Analysis Data Reviewer's Guide - Portfolio Submission Handoff", title),
        Paragraph(f"Study: <b>{study_id}</b> &nbsp;&nbsp; Package version: <b>v0.28.0</b>", body),
        Paragraph(f"Exact GitHub evidence head: <font name='Courier'>{target_sha}</font>", small),
        Paragraph("1. Purpose and evidence boundary", h1),
        Paragraph(
            "This ADRG-style document is a reviewer-orientation artefact for a public-data statistical-programming portfolio. "
            "It summarises the analysis datasets, transport files, Define-XML, validation evidence, traceability, and known limitations. "
            "It is deliberately not represented as a regulatory submission or a validated production deliverable.",
            body,
        ),
        Paragraph("2. Analysis datasets and transport files", h1),
    ]
    table_data = [["Dataset", "Rows", "Transport", "Writer"]]
    for dataset in ["ADSL", "ADAE", "ADQS", "ADTTE"]:
        table_data.append(
            [dataset, str(dataset_rows.get(dataset, 0)), f"{dataset.lower()}.xpt", "SAS LIBNAME XPORT v5"]
        )
    table = Table(table_data, colWidths=[32 * mm, 24 * mm, 42 * mm, 65 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend(
        [
            table,
            Spacer(1, 4 * mm),
            Paragraph("3. Define-XML and Pinnacle 21 validation", h1),
            Paragraph(
                f"Define-XML 2.1 metadata is supplied as <b>define.xml</b>. Pinnacle 21 Community "
                f"{p21.get('pinnacle21_community_version', '4.2.0')} executed on the same controlled package lineage and reported "
                f"<b>{p21.get('reported_occurrences', 'unknown')}</b> finding occurrences. The validator environment warning, if present, "
                "is retained in the evidence package rather than suppressed.",
                body,
            ),
            Paragraph("4. Programming and analysis traceability", h1),
            Paragraph(
                "The portfolio retains programming specifications, analysis-dataset review, SAP-to-TLF traceability, independent Python/R reconstruction, "
                "and real SAS OnDemand execution/reconciliation evidence. Selected TFL and QC outputs are placed outside the submission-like Module 5 folder "
                "under portfolio_evidence so the regulatory-style folder is not confused with a true submission sequence.",
                body,
            ),
            Paragraph("5. XPORT production and QC", h1),
            Paragraph(
                f"Four XPORT v5 files were written by {xpt.get('xport_writer', 'SAS LIBNAME XPORT')} in "
                f"{xpt.get('sas_runtime', 'SAS OnDemand for Academics')} and independently read back on the GitHub runner. "
                f"Round-trip dataset gates passed: <b>{xpt.get('datasets_roundtrip_passed', 'unknown')}/{xpt.get('datasets_exported', 'unknown')}</b>.",
                body,
            ),
            Paragraph("6. Incoming transfer and release control", h1),
            Paragraph(
                "A deterministic public-data transfer fixture demonstrates receipt control: a deliberately defective v1 transfer is rejected and quarantined; "
                "the corrected v2 transfer must pass the same checks before release. This is workflow evidence, not a claim of an actual external vendor transfer.",
                body,
            ),
            Paragraph("7. Known limitations", h1),
            Paragraph(EVIDENCE_BOUNDARY, body),
            Paragraph(
                "Pinnacle 21 Community is executed on a GitHub-hosted Windows Server runner and its unsupported-OS environment warning is retained. "
                "The package is not transmitted through FDA ESG/eCTD infrastructure and has not undergone agency review.",
                body,
            ),
        ]
    )
    doc.build(story)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clinical-dir", required=True)
    parser.add_argument("--p21-dir", required=True)
    parser.add_argument("--sas-dir", required=True)
    parser.add_argument("--transfer-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--target-sha", required=True)
    args = parser.parse_args()

    clinical = Path(args.clinical_dir)
    p21 = Path(args.p21_dir)
    sas = Path(args.sas_dir)
    transfer = Path(args.transfer_dir)
    output = Path(args.output_dir)
    package = output / "submission_package_v0_28"
    if package.exists():
        shutil.rmtree(package)
    package.mkdir(parents=True)

    adsl = pd.read_csv(_find(clinical, "adsl_style.csv"), keep_default_na=False)
    study_ids = sorted(set(adsl["STUDYID"].astype(str)))
    if len(study_ids) != 1:
        raise SystemExit(f"Expected one STUDYID for submission handoff, found {study_ids}")
    study_id = study_ids[0]
    study_slug = _slug(study_id)
    adam_dir = package / "m5" / "datasets" / study_slug / "analysis" / "adam"
    evidence_tfl = package / "portfolio_evidence" / "tfl"
    evidence_qc = package / "portfolio_evidence" / "qc"
    evidence_transfer = package / "portfolio_evidence" / "transfer_control"
    manifest_dir = package / "manifest"
    for directory in [adam_dir, evidence_tfl, evidence_qc, evidence_transfer, manifest_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    p21_metrics = _json(_find(p21, "pinnacle21_validation_metrics.json"))
    xpt_metrics = _json(_find(sas, "submission_xpt_v0_28_metrics.json"))
    transfer_metrics = _json(_find(transfer, "vendor_transfer_metrics.json"))
    p21_clean = bool(p21_metrics.get("runtime_executed")) and int(p21_metrics.get("reported_occurrences", -1)) == 0
    xpt_clean = bool(xpt_metrics.get("all_required_passed")) and int(xpt_metrics.get("datasets_roundtrip_passed", 0)) == 4
    transfer_clean = bool(transfer_metrics.get("reject_then_release_passed"))

    dataset_rows: dict[str, int] = {}
    for dataset, source_name in DATASET_SOURCE_NAMES.items():
        source = _find(clinical, source_name)
        dataset_rows[dataset] = int(len(pd.read_csv(source, keep_default_na=False)))
        xpt = _find(sas, f"{dataset.lower()}.xpt")
        shutil.copy2(xpt, adam_dir / f"{dataset.lower()}.xpt")

    projected_define = next(p21.rglob("define_xml_candidate_v0_28_submission.xml"), None)
    define_source = projected_define or _find(p21, "define_xml_candidate_v0_27_round4.xml")
    shutil.copy2(define_source, adam_dir / "define.xml")
    _make_adrg_pdf(
        adam_dir / "adrg.pdf",
        study_id,
        dataset_rows,
        p21_metrics,
        xpt_metrics,
        args.target_sha,
    )
    adrg_md = (
        "# Analysis Data Reviewer's Guide - Portfolio Submission Handoff\n\n"
        f"- Study: `{study_id}`\n"
        f"- Exact evidence head: `{args.target_sha}`\n"
        f"- P21 findings: `{p21_metrics.get('reported_occurrences')}`\n"
        f"- SAS XPORT v5 round-trip: `{xpt_metrics.get('datasets_roundtrip_passed')}/{xpt_metrics.get('datasets_exported')}`\n\n"
        f"Evidence boundary: {EVIDENCE_BOUNDARY}\n"
    )
    (adam_dir / "adrg.md").write_text(adrg_md, encoding="utf-8")

    for name in SELECTED_TFLS:
        _copy_if_present(clinical, name, evidence_tfl / name)
    for name in SELECTED_QC:
        _copy_if_present(clinical, name, evidence_qc / name)
    for name in [
        "pinnacle21_define_report.xlsx",
        "pinnacle21_validation_summary.md",
        "pinnacle21_validation_metrics.json",
        "pinnacle21_issue_summary.csv",
    ]:
        _copy_if_present(p21, name, evidence_qc / name)
    for name in [
        "submission_xpt_v0_28_qc.csv",
        "submission_xpt_v0_28_metrics.json",
        "submission_xpt_v0_28_summary.md",
        "sas_oda_execution_qc.csv",
        "sas_oda_validation_summary.md",
    ]:
        _copy_if_present(sas, name, evidence_qc / name)
    for path in transfer.iterdir():
        if path.is_file():
            shutil.copy2(path, evidence_transfer / path.name)

    handoff = (
        "# v0.28 programming handoff\n\n"
        f"Study: `{study_id}`  \nExact evidence head: `{args.target_sha}`\n\n"
        "## Release contents\n"
        "- Four SAS-written XPORT v5 analysis transport files.\n"
        "- Define-XML 2.1 as `define.xml`.\n"
        "- ADRG-style reviewer guide as `adrg.pdf` plus source markdown.\n"
        "- Selected TFL, QC, P21, SAS ODA reconciliation, and vendor-transfer receipt evidence under `portfolio_evidence/`.\n\n"
        "## Release boundary\n"
        f"{EVIDENCE_BOUNDARY}\n"
    )
    (package / "PROGRAMMING_HANDOFF.md").write_text(handoff, encoding="utf-8")

    qc_rows = [
        {
            "check": "pinnacle21_clean_report",
            "passed": p21_clean,
            "required": True,
            "detail": f"reported_occurrences={p21_metrics.get('reported_occurrences')}",
        },
        {
            "check": "four_sas_xport_v5_roundtrips",
            "passed": xpt_clean,
            "required": True,
            "detail": f"passed={xpt_metrics.get('datasets_roundtrip_passed')}/{xpt_metrics.get('datasets_exported')}",
        },
        {
            "check": "define_xml_present",
            "passed": (adam_dir / "define.xml").exists(),
            "required": True,
            "detail": "Define-XML 2.1 portfolio candidate",
        },
        {
            "check": "adrg_pdf_present",
            "passed": (adam_dir / "adrg.pdf").exists() and (adam_dir / "adrg.pdf").stat().st_size > 0,
            "required": True,
            "detail": "ADRG-style PDF generated",
        },
        {
            "check": "vendor_receipt_reject_then_release",
            "passed": transfer_clean,
            "required": True,
            "detail": f"v1={transfer_metrics.get('v1_decision')}; v2={transfer_metrics.get('v2_decision')}",
        },
        {
            "check": "exact_head_recorded",
            "passed": len(args.target_sha) == 40,
            "required": True,
            "detail": args.target_sha,
        },
    ]
    qc = pd.DataFrame(qc_rows)
    qc.to_csv(evidence_qc / "submission_handoff_v0_28_qc.csv", index=False)
    all_required = bool(qc.loc[qc["required"].eq(True), "passed"].all())

    manifest_rows: list[dict[str, object]] = []
    for path in sorted(p for p in package.rglob("*") if p.is_file()):
        rel = path.relative_to(package).as_posix()
        manifest_rows.append(
            {
                "relative_path": rel,
                "category": rel.split("/", 1)[0],
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    manifest_path = manifest_dir / "sha256_manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["relative_path", "category", "bytes", "sha256"],
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    metrics = {
        "version": "0.28.0",
        "study_id": study_id,
        "target_sha": args.target_sha,
        "analysis_datasets": dataset_rows,
        "xpt_files": 4,
        "pinnacle21_reported_occurrences": int(p21_metrics.get("reported_occurrences", -1)),
        "vendor_reject_then_release_passed": transfer_clean,
        "required_checks": int(len(qc.loc[qc["required"].eq(True)])),
        "required_passed": int(qc.loc[qc["required"].eq(True), "passed"].sum()),
        "manifest_entries": len(manifest_rows),
        "all_required_passed": all_required,
        "controlled_claim": CONTROLLED_CLAIM if all_required else None,
        "evidence_boundary": EVIDENCE_BOUNDARY,
    }
    (package / "submission_handoff_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    release = (
        "# v0.28 submission-style handoff release decision\n\n"
        f"- Required gates: **{metrics['required_passed']}/{metrics['required_checks']}**\n"
        f"- P21 reported occurrences: **{metrics['pinnacle21_reported_occurrences']}**\n"
        f"- SAS XPORT v5 files: **{metrics['xpt_files']}**\n"
        f"- Vendor receipt reject-then-release gate: **{metrics['vendor_reject_then_release_passed']}**\n"
        f"- Controlled claim: `{metrics['controlled_claim']}`\n\n"
        f"Evidence boundary: {EVIDENCE_BOUNDARY}\n"
    )
    (package / "RELEASE_DECISION.md").write_text(release, encoding="utf-8")

    archive_base = output / "submission_package_v0_28"
    shutil.make_archive(str(archive_base), "zip", root_dir=package)
    zip_path = output / "submission_package_v0_28.zip"
    (output / "submission_package_v0_28.zip.sha256").write_text(
        _sha256(zip_path) + "  submission_package_v0_28.zip\n",
        encoding="utf-8",
    )
    print(json.dumps(metrics, indent=2, sort_keys=True))
    if not all_required:
        raise SystemExit(
            "v0.28 submission handoff gate failed; inspect portfolio_evidence/qc/submission_handoff_v0_28_qc.csv"
        )


if __name__ == "__main__":
    main()
