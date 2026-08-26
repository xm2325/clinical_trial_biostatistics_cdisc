from __future__ import annotations

import argparse
import csv
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "spec" / "submission_projection_v0_28.json"
ODM_NS = "http://www.cdisc.org/ns/odm/v1.3"
DEF_NS = "http://www.cdisc.org/ns/def/v2.1"
XLINK_NS = "http://www.w3.org/1999/xlink"

ET.register_namespace("", ODM_NS)
ET.register_namespace("def", DEF_NS)
ET.register_namespace("xlink", XLINK_NS)


def _find(root: Path, name: str) -> Path:
    hit = next(root.rglob(name), None)
    if hit is None:
        raise FileNotFoundError(f"Required file {name} not found under {root}")
    return hit


def _load_spec() -> dict[str, object]:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def _dataset_item_oids(meta: ET.Element, dataset: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in meta.findall(f"{{{ODM_NS}}}ItemDef"):
        oid = item.get("OID", "")
        if oid.startswith(f"IT.{dataset}."):
            out[item.get("Name", "")] = oid
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    spec = _load_spec()
    dataset_specs = spec["datasets"]

    define_source = _find(artifact_dir, "define_xml_candidate_v0_26.xml")
    tree = ET.parse(define_source)
    root = tree.getroot()
    meta = root.find(f"{{{ODM_NS}}}Study/{{{ODM_NS}}}MetaDataVersion")
    if meta is None:
        raise SystemExit("MetaDataVersion not found in remediated Define-XML")

    inventory: list[dict[str, object]] = []
    excluded_item_oids: set[str] = set()
    dataset_metrics: dict[str, dict[str, object]] = {}

    for dataset, cfg in dataset_specs.items():
        source_name = cfg["source_file"]
        excluded = list(cfg["exclude_from_submission"])
        source = _find(artifact_dir, source_name)
        frame = pd.read_csv(source, keep_default_na=False)
        missing_exclusions = sorted(set(excluded).difference(frame.columns))
        if missing_exclusions:
            raise RuntimeError(f"{dataset}: expected excluded variables missing from controlled source: {missing_exclusions}")

        actual_long = sorted(col for col in frame.columns if len(col) > 8)
        if sorted(excluded) != actual_long:
            raise RuntimeError(
                f"{dataset}: projection spec must explicitly cover every >8-char variable and only those variables; "
                f"spec={sorted(excluded)} actual={actual_long}"
            )

        projected = frame.drop(columns=excluded)
        remaining_long = sorted(col for col in projected.columns if len(col) > 8)
        if remaining_long:
            raise RuntimeError(f"{dataset}: submission projection still has >8-char variables: {remaining_long}")

        alias_name = f"{dataset}.csv"
        projected.to_csv(artifact_dir / alias_name, index=False)
        projected.to_csv(output_dir / alias_name, index=False)

        item_oids = _dataset_item_oids(meta, dataset)
        missing_define = sorted(set(excluded).difference(item_oids))
        if missing_define:
            raise RuntimeError(f"{dataset}: excluded variables missing from Define-XML: {missing_define}")
        for variable in excluded:
            excluded_item_oids.add(item_oids[variable])

        for col in frame.columns:
            inventory.append(
                {
                    "dataset": dataset,
                    "variable": col,
                    "source_name_length": len(col),
                    "submission_status": "EXCLUDED_AUDIT_HELPER_XPT_V5_LIMIT" if col in excluded else "INCLUDED",
                    "submission_variable": "" if col in excluded else col,
                }
            )

        dataset_metrics[dataset] = {
            "source_rows": int(len(frame)),
            "source_columns": int(len(frame.columns)),
            "excluded_columns": excluded,
            "submission_columns": int(len(projected.columns)),
            "all_submission_names_le_8": all(len(col) <= 8 for col in projected.columns),
        }

    # Remove the excluded variables from each ItemGroupDef.
    removed_itemrefs = 0
    for group in meta.findall(f"{{{ODM_NS}}}ItemGroupDef"):
        for ref in list(group.findall(f"{{{ODM_NS}}}ItemRef")):
            if ref.get("ItemOID") in excluded_item_oids:
                group.remove(ref)
                removed_itemrefs += 1

    # Remove the corresponding ItemDefs. The full source datasets and audit variables remain
    # available outside the submission-style Module 5 projection as portfolio/QC evidence.
    removed_itemdefs = 0
    for item in list(meta.findall(f"{{{ODM_NS}}}ItemDef")):
        if item.get("OID") in excluded_item_oids:
            meta.remove(item)
            removed_itemdefs += 1

    if removed_itemrefs != len(excluded_item_oids) or removed_itemdefs != len(excluded_item_oids):
        raise RuntimeError(
            f"Define projection removal mismatch: excluded={len(excluded_item_oids)} "
            f"itemrefs={removed_itemrefs} itemdefs={removed_itemdefs}"
        )

    remaining_item_oids = {item.get("OID") for item in meta.findall(f"{{{ODM_NS}}}ItemDef")}
    dangling_refs = [
        ref.get("ItemOID")
        for group in meta.findall(f"{{{ODM_NS}}}ItemGroupDef")
        for ref in group.findall(f"{{{ODM_NS}}}ItemRef")
        if ref.get("ItemOID") not in remaining_item_oids
    ]
    if dangling_refs:
        raise RuntimeError(f"Define submission projection has dangling ItemRefs: {dangling_refs}")

    bad_item_names: list[str] = []
    bad_sas_names: list[str] = []
    name_mismatches: list[str] = []
    for item in meta.findall(f"{{{ODM_NS}}}ItemDef"):
        name = item.get("Name", "")
        sas_name = item.get("SASFieldName", "")
        if len(name) > 8:
            bad_item_names.append(name)
        if len(sas_name) > 8:
            bad_sas_names.append(sas_name)
        if name != sas_name:
            name_mismatches.append(f"{name}->{sas_name}")
    if bad_item_names or bad_sas_names or name_mismatches:
        raise RuntimeError(
            "Submission Define must match physical XPORT variable names exactly after projection; "
            f"bad_names={bad_item_names}, bad_sas={bad_sas_names}, mismatches={name_mismatches}"
        )

    ET.indent(tree, space="  ")
    xml_text = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"
    define_source.write_text(xml_text, encoding="utf-8", newline="\n")
    final_define = output_dir / "define_xml_candidate_v0_28_submission.xml"
    shutil.copy2(define_source, final_define)

    inventory_path = output_dir / "submission_projection_v0_28_variable_inventory.csv"
    with inventory_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["dataset", "variable", "source_name_length", "submission_status", "submission_variable"],
        )
        writer.writeheader()
        writer.writerows(inventory)

    manifest = {
        "version": "0.28.0",
        "policy": spec["policy"],
        "datasets": dataset_metrics,
        "excluded_itemdefs": removed_itemdefs,
        "excluded_itemrefs": removed_itemrefs,
        "submission_define": final_define.name,
        "all_physical_variable_names_le_8": True,
        "define_name_sasfieldname_identity": True,
        "evidence_boundary": spec["evidence_boundary"],
    }
    (output_dir / "submission_projection_v0_28_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
