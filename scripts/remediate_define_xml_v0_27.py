from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

ODM_NS = "http://www.cdisc.org/ns/odm/v1.3"
DEF_NS = "http://www.cdisc.org/ns/def/v2.1"
XLINK_NS = "http://www.w3.org/1999/xlink"
XML_NS = "http://www.w3.org/XML/1998/namespace"

ET.register_namespace("", ODM_NS)
ET.register_namespace("def", DEF_NS)
ET.register_namespace("xlink", XLINK_NS)

BASELINE_RUN_ID = 32943049927
BASELINE_ARTIFACT_ID = 9597406026
BASELINE_ARTIFACT_DIGEST = "sha256:6bcca11ed53310d50500ca4e1acc10c3753451903b9482d72a167eebf18392fa"
BASELINE_ISSUE_CLASSES = 15
BASELINE_OCCURRENCES = 226

DATASET_FILES = {
    "ADSL": "adsl_style.csv",
    "ADAE": "adae_style.csv",
    "ADQS": "adqs_actot_style.csv",
    "ADTTE": "adtte_retention_style.csv",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _description(parent: ET.Element, text: str, index: int = 0) -> None:
    existing = parent.find(f"{{{ODM_NS}}}Description")
    if existing is not None:
        return
    desc = ET.Element(f"{{{ODM_NS}}}Description")
    translated = ET.SubElement(desc, f"{{{ODM_NS}}}TranslatedText")
    translated.set(f"{{{XML_NS}}}lang", "en")
    translated.text = text
    parent.insert(index, desc)


def _sas_field_name(name: str, used: set[str]) -> str:
    clean = "".join(ch for ch in name.upper() if ch.isalnum() or ch == "_")
    if len(clean) <= 8 and clean not in used:
        used.add(clean)
        return clean
    base = clean[:8]
    if base and base not in used:
        used.add(base)
        return base
    stem = (clean[:5] or "VAR").ljust(5, "X")
    for i in range(1, 1000):
        candidate = f"{stem}{i:03d}"[:8]
        if candidate not in used:
            used.add(candidate)
            return candidate
    raise RuntimeError(f"Could not allocate unique SASFieldName for {name}")


def _insert_standards(meta: ET.Element) -> None:
    old_name = f"{{{DEF_NS}}}StandardName"
    old_version = f"{{{DEF_NS}}}StandardVersion"
    meta.attrib.pop(old_name, None)
    meta.attrib.pop(old_version, None)

    for child in list(meta):
        if child.tag == f"{{{DEF_NS}}}Standards":
            meta.remove(child)

    standards = ET.Element(f"{{{DEF_NS}}}Standards")
    ET.SubElement(
        standards,
        f"{{{DEF_NS}}}Standard",
        {
            "OID": "STD.ADAMIG.1.3",
            "Name": "ADaMIG",
            "Type": "IG",
            "Version": "1.3",
            "Status": "Final",
        },
    )
    ET.SubElement(
        standards,
        f"{{{DEF_NS}}}Standard",
        {
            "OID": "STD.CT.ADAM.2025-03-28",
            "Name": "CDISC/NCI",
            "Type": "CT",
            "PublishingSet": "ADaM",
            "Version": "2025-03-28",
            "Status": "Final",
        },
    )
    meta.insert(0, standards)


def _remediate_item_groups(meta: ET.Element) -> dict[str, int]:
    counts = {
        "item_groups": 0,
        "item_refs": 0,
        "key_sequences": 0,
        "dataset_descriptions": 0,
        "leaves": 0,
    }
    for group in meta.findall(f"{{{ODM_NS}}}ItemGroupDef"):
        counts["item_groups"] += 1
        dataset = group.get("Name", "")
        group.attrib.pop(f"{{{DEF_NS}}}Class", None)
        group.set("Purpose", "Analysis")
        group.set(f"{{{DEF_NS}}}IsNonStandard", "Yes")
        group.set(f"{{{DEF_NS}}}StandardOID", "STD.ADAMIG.1.3")
        if group.find(f"{{{ODM_NS}}}Description") is None:
            _description(group, f"Portfolio {dataset} analysis dataset", 0)
            counts["dataset_descriptions"] += 1

        for ref in group.findall(f"{{{ODM_NS}}}ItemRef"):
            counts["item_refs"] += 1
            old_key = ref.attrib.pop(f"{{{DEF_NS}}}KeySequence", None)
            if old_key is not None and str(old_key).strip():
                ref.set("KeySequence", str(old_key).strip())
                counts["key_sequences"] += 1

        for leaf in list(group):
            if leaf.tag == f"{{{DEF_NS}}}leaf":
                group.remove(leaf)
        leaf_id = group.get(f"{{{DEF_NS}}}ArchiveLocationID") or f"LF.{dataset}"
        group.set(f"{{{DEF_NS}}}ArchiveLocationID", leaf_id)
        leaf = ET.SubElement(
            group,
            f"{{{DEF_NS}}}leaf",
            {
                "ID": leaf_id,
                f"{{{XLINK_NS}}}href": DATASET_FILES.get(dataset, f"{dataset.lower()}.csv"),
            },
        )
        ET.SubElement(leaf, f"{{{DEF_NS}}}title").text = DATASET_FILES.get(dataset, f"{dataset.lower()}.csv")
        counts["leaves"] += 1
    return counts


def _remediate_item_defs(meta: ET.Element) -> dict[str, int]:
    counts = {
        "item_defs": 0,
        "variable_descriptions": 0,
        "numeric_lengths": 0,
        "significant_digits": 0,
        "short_sas_field_names": 0,
    }
    used_by_dataset: dict[str, set[str]] = {}
    for item in meta.findall(f"{{{ODM_NS}}}ItemDef"):
        counts["item_defs"] += 1
        oid = item.get("OID", "")
        parts = oid.split(".")
        dataset = parts[1] if len(parts) >= 3 else "GLOBAL"
        variable = item.get("Name", parts[-1] if parts else "VARIABLE")
        used = used_by_dataset.setdefault(dataset, set())
        sas_name = _sas_field_name(variable, used)
        if item.get("SASFieldName") != sas_name:
            counts["short_sas_field_names"] += 1
        item.set("SASFieldName", sas_name)

        if item.find(f"{{{ODM_NS}}}Description") is None:
            _description(item, variable, 0)
            counts["variable_descriptions"] += 1

        data_type = (item.get("DataType") or "").lower()
        if data_type in {"integer", "float"} and not item.get("Length"):
            item.set("Length", "8")
            counts["numeric_lengths"] += 1
        if data_type == "float" and not item.get("SignificantDigits"):
            item.set("SignificantDigits", "8")
            counts["significant_digits"] += 1
    return counts


def _assert_structure(root: ET.Element, meta: ET.Element) -> dict[str, bool]:
    groups = meta.findall(f"{{{ODM_NS}}}ItemGroupDef")
    items = meta.findall(f"{{{ODM_NS}}}ItemDef")
    standards = meta.find(f"{{{DEF_NS}}}Standards")
    checks = {
        "context_other": root.get(f"{{{DEF_NS}}}Context") == "Other",
        "deprecated_standard_attrs_removed": (
            f"{{{DEF_NS}}}StandardName" not in meta.attrib
            and f"{{{DEF_NS}}}StandardVersion" not in meta.attrib
        ),
        "standards_present": standards is not None and len(list(standards)) >= 2,
        "dataset_descriptions_present": all(g.find(f"{{{ODM_NS}}}Description") is not None for g in groups),
        "dataset_nonstandard_explicit": all(g.get(f"{{{DEF_NS}}}IsNonStandard") == "Yes" for g in groups),
        "dataset_leaf_present": all(g.find(f"{{{DEF_NS}}}leaf") is not None for g in groups),
        "deprecated_class_removed": all(f"{{{DEF_NS}}}Class" not in g.attrib for g in groups),
        "deprecated_keysequence_removed": all(
            f"{{{DEF_NS}}}KeySequence" not in ref.attrib
            for g in groups
            for ref in g.findall(f"{{{ODM_NS}}}ItemRef")
        ),
        "variable_descriptions_present": all(i.find(f"{{{ODM_NS}}}Description") is not None for i in items),
        "sas_field_names_valid": all(0 < len(i.get("SASFieldName", "")) <= 8 for i in items),
        "numeric_lengths_present": all(
            i.get("DataType", "").lower() not in {"integer", "float"} or bool(i.get("Length"))
            for i in items
        ),
        "float_significant_digits_present": all(
            i.get("DataType", "").lower() != "float" or bool(i.get("SignificantDigits"))
            for i in items
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"Define-XML v0.27 structural remediation assertions failed: {failed}")
    return checks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    source = next(artifact_dir.rglob("define_xml_candidate_v0_26.xml"), None)
    if source is None:
        raise SystemExit(f"define_xml_candidate_v0_26.xml not found under {artifact_dir}")

    baseline_copy = output_dir / "define_xml_candidate_v0_26_baseline.xml"
    shutil.copy2(source, baseline_copy)
    baseline_sha = _sha256(baseline_copy)

    tree = ET.parse(source)
    root = tree.getroot()
    root.set(f"{{{DEF_NS}}}Context", "Other")
    meta = root.find(f"{{{ODM_NS}}}Study/{{{ODM_NS}}}MetaDataVersion")
    if meta is None:
        raise SystemExit("MetaDataVersion not found in Define-XML candidate")
    meta.set("Description", "Portfolio ADaM metadata remediated after real Pinnacle 21 Community review")

    _insert_standards(meta)
    group_counts = _remediate_item_groups(meta)
    item_counts = _remediate_item_defs(meta)
    checks = _assert_structure(root, meta)

    ET.indent(tree, space="  ")
    body = ET.tostring(root, encoding="unicode")
    remediated_text = '<?xml version="1.0" encoding="UTF-8"?>\n' + body + "\n"
    source.write_text(remediated_text, encoding="utf-8", newline="\n")
    remediated_copy = output_dir / "define_xml_candidate_v0_27.xml"
    shutil.copy2(source, remediated_copy)

    manifest = {
        "version": "0.27.0",
        "baseline_reference": {
            "pinnacle21_run_id": BASELINE_RUN_ID,
            "artifact_id": BASELINE_ARTIFACT_ID,
            "artifact_digest": BASELINE_ARTIFACT_DIGEST,
            "issue_classes": BASELINE_ISSUE_CLASSES,
            "occurrences": BASELINE_OCCURRENCES,
        },
        "baseline_define_sha256": baseline_sha,
        "remediated_define_sha256": _sha256(remediated_copy),
        "targeted_findings": [
            "DD0003 Context/SASFieldName",
            "DD0004 deprecated def:Class/def:KeySequence/StandardName/StandardVersion",
            "DD0006 Standards/def:leaf",
            "DD0057 dataset Description",
            "DD0058 variable Label/Description",
            "DD0121 IsNonStandard",
            "DD0150 expected ADaM standards",
            "OD0011 XML encoding",
            "OD0070 numeric Length",
            "OD0071 SignificantDigits",
        ],
        "group_changes": group_counts,
        "item_changes": item_counts,
        "structural_assertions": checks,
        "evidence_boundary": (
            "Remediation is driven by real Pinnacle 21 Community findings on a public-data portfolio candidate. "
            "It does not establish formal ADaM conformance, validated GxP execution, or submission readiness."
        ),
    }
    (output_dir / "define_xml_remediation_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
