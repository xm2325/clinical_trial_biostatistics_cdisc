from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def find_one(root: Path, name: str) -> Path:
    hit = next(root.rglob(name), None)
    if hit is None:
        raise FileNotFoundError(f"Required file {name} not found under {root}")
    return hit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p21-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--upstream-identity", required=True)
    args = parser.parse_args()

    p21_dir = Path(args.p21_dir)
    output_dir = Path(args.output_dir)
    package = output_dir / "submission_package_v0_28"
    if not package.exists():
        raise SystemExit(f"Submission package not found: {package}")

    projection_manifest_path = find_one(p21_dir, "submission_projection_v0_28_manifest.json")
    projection_manifest = json.loads(projection_manifest_path.read_text(encoding="utf-8-sig"))
    projection_ok = bool(projection_manifest.get("all_physical_variable_names_le_8")) and bool(
        projection_manifest.get("define_name_sasfieldname_identity")
    )
    if not projection_ok:
        raise SystemExit(f"v0.28 submission projection is not releaseable: {projection_manifest}")

    projected_define = find_one(p21_dir, "define_xml_candidate_v0_28_submission.xml")
    adam_dir = next(package.rglob("analysis/adam"), None)
    if adam_dir is None:
        raise SystemExit("Module 5 analysis/adam directory not found in package")
    shutil.copy2(projected_define, adam_dir / "define.xml")

    qc_dir = package / "portfolio_evidence" / "qc"
    qc_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(projection_manifest_path, qc_dir / projection_manifest_path.name)
    projection_inventory = find_one(p21_dir, "submission_projection_v0_28_variable_inventory.csv")
    shutil.copy2(projection_inventory, qc_dir / projection_inventory.name)

    identity_src = Path(args.upstream_identity)
    if not identity_src.exists():
        raise SystemExit(f"Upstream identity file not found: {identity_src}")
    manifest_dir = package / "manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(identity_src, manifest_dir / "upstream_identity.txt")

    metrics_path = package / "submission_handoff_metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    excluded_count = sum(len(d.get("excluded_columns", [])) for d in projection_manifest.get("datasets", {}).values())
    metrics["submission_projection_validated"] = True
    metrics["xport_v5_excluded_audit_helper_variables"] = int(excluded_count)
    metrics["define_xml_source"] = "define_xml_candidate_v0_28_submission.xml"
    metrics["manifest_scope"] = "all final package files except sha256_manifest.csv itself"
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    release_path = package / "RELEASE_DECISION.md"
    release = release_path.read_text(encoding="utf-8")
    release += (
        "\n## v0.28 XPORT/Define projection\n"
        f"- FDA XPORT v5-compatible physical variable-name projection: **PASS**\n"
        f"- Long-name non-submission audit/helper variables excluded explicitly: **{excluded_count}**\n"
        "- Final `define.xml` is the same projected Define lineage validated by the v0.28 Pinnacle 21 workflow.\n"
        "- Full unprojected analysis datasets remain in portfolio/QC evidence and are not represented as submission transports.\n"
    )
    release_path.write_text(release, encoding="utf-8")

    manifest_path = manifest_dir / "sha256_manifest.csv"
    if manifest_path.exists():
        manifest_path.unlink()
    rows: list[dict[str, object]] = []
    for path in sorted(p for p in package.rglob("*") if p.is_file() and p != manifest_path):
        rel = path.relative_to(package).as_posix()
        rows.append(
            {
                "relative_path": rel,
                "category": rel.split("/", 1)[0],
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["relative_path", "category", "bytes", "sha256"])
        writer.writeheader()
        writer.writerows(rows)

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics["final_manifest_entries"] = len(rows)
    # Updating metrics changes its digest, so refresh its manifest row once, then rewrite the manifest.
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for row in rows:
        if row["relative_path"] == "submission_handoff_metrics.json":
            row["bytes"] = metrics_path.stat().st_size
            row["sha256"] = sha256(metrics_path)
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["relative_path", "category", "bytes", "sha256"])
        writer.writeheader()
        writer.writerows(rows)

    archive_base = output_dir / "submission_package_v0_28"
    zip_path = output_dir / "submission_package_v0_28.zip"
    sha_path = output_dir / "submission_package_v0_28.zip.sha256"
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(archive_base), "zip", root_dir=package)
    sha_path.write_text(f"{sha256(zip_path)}  {zip_path.name}\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "submission_projection_validated": True,
                "excluded_audit_helper_variables": excluded_count,
                "final_manifest_entries": len(rows),
                "final_define": str((adam_dir / "define.xml").relative_to(package)),
                "zip_sha256": sha256(zip_path),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
