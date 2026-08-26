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

ROUND1_RUN_ID = 32944960784
ROUND1_ARTIFACT_ID = 9598114460
ROUND1_ARTIFACT_DIGEST = "sha256:9e26cea713e6d7b411bc5777138a12a6ba2731b05c62c0670535880d32c9d778"
ROUND1_ISSUE_CLASSES = 6
ROUND1_OCCURRENCES = 103

SOURCE_DATASET_FILES = {
    "ADSL": "adsl_style.csv",
    "ADAE": "adae_style.csv",
    "ADQS": "adqs_actot_style.csv",
    "ADTTE": "adtte_retention_style.csv",
}
VALIDATION_DATASET_FILES = {dataset: f"{dataset}.csv" for dataset in SOURCE_DATASET_FILES}

DATASET_CLASSES = {
    "ADSL": "SUBJECT LEVEL ANALYSIS DATASET",
    "ADAE": "OCCURRENCE DATA STRUCTURE",
    "ADQS": "BASIC DATA STRUCTURE",
    "ADTTE": "BASIC DATA STRUCTURE",
}

SDTM_PREDECESSOR_VARS = {
    "ADSL": {"STUDYID", "USUBJID", "AGE", "SEX", "RACE", "COUNTRY", "TRT01P", "TRT01A"},
    "ADAE": {"STUDYID", "USUBJID", "AESEQ", "AETERM", "AEDECOD", "AEBODSYS", "AESEV", "AESER", "AEREL", "AEOUT"},
    "ADQS": {"STUDYID", "USUBJID", "QSSEQ"},
    "ADTTE": {"STUDYID", "USUBJID"},
}
ANALYSIS_PREDECESSOR_VARS = {
    "ADAE": {"TRT01A", "TRTSDT", "TRTEDT", "SAFFL"},
    "ADTTE": {"TRT01P", "TRT01A", "SAFFL"},
}

STANDARD_CODELISTS = {
    "CL.NY": {
        "name": "No Yes Response",
        "terms": [("N", "No"), ("Y", "Yes")],
    },
    "CL.AESEV": {
        "name": "Adverse Event Severity/Intensity Scale",
        "terms": [("MILD", "Mild"), ("MODERATE", "Moderate"), ("SEVERE", "Severe")],
    },
    "CL.RACE": {
        "name": "Race",
        "terms": [
            ("AMERICAN INDIAN OR ALASKA NATIVE", "American Indian or Alaska Native"),
            ("ASIAN", "Asian"),
            ("BLACK OR AFRICAN AMERICAN", "Black or African American"),
            ("WHITE", "White"),
        ],
    },
    "CL.SEX": {
        "name": "Sex",
        "terms": [("F", "Female"), ("M", "Male")],
    },
}
VARIABLE_CODELISTS = {
    ("ADAE", "AESER"): "CL.NY",
    ("ADAE", "AESEV"): "CL.AESEV",
    ("ADSL", "RACE"): "CL.RACE",
    ("ADSL", "SEX"): "CL.SEX",
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
    meta.attrib.pop(f"{{{DEF_NS}}}StandardName", None)
    meta.attrib.pop(f"{{{DEF_NS}}}StandardVersion", None)
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
            "Name": "ADaM",
            "Type": "CT",
            "PublishingSet": "ADaM",
            "Version": "2025-03-28",
            "Status": "Final",
        },
    )
    meta.insert(0, standards)


def _copy_validation_aliases(artifact_dir: Path, define_dir: Path, output_dir: Path) -> dict[str, str]:
    copied: dict[str, str] = {}
    for dataset, source_name in SOURCE_DATASET_FILES.items():
        source = next(artifact_dir.rglob(source_name), None)
        if source is None:
            raise RuntimeError(f"Expected controlled dataset {source_name} not found under {artifact_dir}")
        alias_name = VALIDATION_DATASET_FILES[dataset]
        alias = define_dir / alias_name
        shutil.copy2(source, alias)
        shutil.copy2(source, output_dir / alias_name)
        copied[dataset] = alias_name
    return copied


def _class_element(group: ET.Element, dataset: str) -> None:
    for child in list(group):
        if child.tag == f"{{{DEF_NS}}}Class":
            group.remove(child)
    klass = ET.Element(f"{{{DEF_NS}}}Class", {"Name": DATASET_CLASSES[dataset]})
    children = list(group)
    insert_at = 1 if children and children[0].tag == f"{{{ODM_NS}}}Description" else 0
    group.insert(insert_at, klass)


def _remediate_item_groups(meta: ET.Element) -> dict[str, int]:
    counts = {
        "item_groups": 0,
        "item_refs": 0,
        "key_sequences": 0,
        "dataset_descriptions": 0,
        "dataset_classes": 0,
        "leaves": 0,
        "is_nonstandard_removed": 0,
    }
    for group in meta.findall(f"{{{ODM_NS}}}ItemGroupDef"):
        counts["item_groups"] += 1
        dataset = group.get("Name", "")
        if dataset not in DATASET_CLASSES:
            raise RuntimeError(f"Unexpected controlled dataset in Define candidate: {dataset}")
        group.attrib.pop(f"{{{DEF_NS}}}Class", None)
        if group.attrib.pop(f"{{{DEF_NS}}}IsNonStandard", None) is not None:
            counts["is_nonstandard_removed"] += 1
        group.set("Purpose", "Analysis")
        group.set(f"{{{DEF_NS}}}StandardOID", "STD.ADAMIG.1.3")
        if group.find(f"{{{ODM_NS}}}Description") is None:
            _description(group, f"Portfolio {dataset} analysis dataset", 0)
            counts["dataset_descriptions"] += 1
        _class_element(group, dataset)
        counts["dataset_classes"] += 1

        method_oid = f"MT.{dataset}.DERIVED"
        for ref in group.findall(f"{{{ODM_NS}}}ItemRef"):
            counts["item_refs"] += 1
            old_key = ref.attrib.pop(f"{{{DEF_NS}}}KeySequence", None)
            if old_key is not None and str(old_key).strip():
                ref.set("KeySequence", str(old_key).strip())
                counts["key_sequences"] += 1
            variable = ref.get("ItemOID", "").split(".")[-1]
            is_sdtm_predecessor = variable in SDTM_PREDECESSOR_VARS.get(dataset, set())
            is_analysis_predecessor = variable in ANALYSIS_PREDECESSOR_VARS.get(dataset, set())
            if is_sdtm_predecessor or is_analysis_predecessor:
                ref.attrib.pop("MethodOID", None)
            else:
                ref.set("MethodOID", method_oid)

        for leaf in list(group):
            if leaf.tag == f"{{{DEF_NS}}}leaf":
                group.remove(leaf)
        leaf_id = group.get(f"{{{DEF_NS}}}ArchiveLocationID") or f"LF.{dataset}"
        group.set(f"{{{DEF_NS}}}ArchiveLocationID", leaf_id)
        filename = VALIDATION_DATASET_FILES[dataset]
        leaf = ET.SubElement(
            group,
            f"{{{DEF_NS}}}leaf",
            {"ID": leaf_id, f"{{{XLINK_NS}}}href": filename},
        )
        ET.SubElement(leaf, f"{{{DEF_NS}}}title").text = filename
        counts["leaves"] += 1
    return counts


def _origin_for(dataset: str, variable: str) -> tuple[str, str, str]:
    if variable in SDTM_PREDECESSOR_VARS.get(dataset, set()):
        return "Predecessor", "SDTM", f"Exact predecessor value carried from the public source domain into portfolio {dataset}."
    if variable in ANALYSIS_PREDECESSOR_VARS.get(dataset, set()):
        return "Predecessor", "Sponsor", f"Exact predecessor value carried from a controlled upstream portfolio analysis dataset into {dataset}."
    return "Derived", "Sponsor", f"Programmatically derived or transformed by the controlled portfolio analysis workflow for {dataset}."


def _insert_origin(item: ET.Element, dataset: str, variable: str) -> None:
    for child in list(item):
        if child.tag == f"{{{DEF_NS}}}Origin":
            item.remove(child)
    origin_type, source, text = _origin_for(dataset, variable)
    origin = ET.Element(f"{{{DEF_NS}}}Origin", {"Type": origin_type, "Source": source})
    desc = ET.SubElement(origin, f"{{{ODM_NS}}}Description")
    translated = ET.SubElement(desc, f"{{{ODM_NS}}}TranslatedText")
    translated.set(f"{{{XML_NS}}}lang", "en")
    translated.text = text
    item.append(origin)


def _insert_codelist_ref(item: ET.Element, codelist_oid: str) -> None:
    for child in list(item):
        if child.tag == f"{{{ODM_NS}}}CodeListRef":
            item.remove(child)
    ref = ET.Element(f"{{{ODM_NS}}}CodeListRef", {"CodeListOID": codelist_oid})
    # Keep Description first, then CodeListRef, then def:Origin.
    children = list(item)
    insert_at = 1 if children and children[0].tag == f"{{{ODM_NS}}}Description" else 0
    item.insert(insert_at, ref)


def _remediate_item_defs(meta: ET.Element) -> dict[str, int]:
    counts = {
        "item_defs": 0,
        "variable_descriptions": 0,
        "numeric_lengths": 0,
        "significant_digits": 0,
        "short_sas_field_names": 0,
        "origins": 0,
        "codelist_refs": 0,
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

        codelist_oid = VARIABLE_CODELISTS.get((dataset, variable))
        if codelist_oid:
            _insert_codelist_ref(item, codelist_oid)
            counts["codelist_refs"] += 1
        _insert_origin(item, dataset, variable)
        counts["origins"] += 1
    return counts


def _insert_codelists(meta: ET.Element) -> int:
    existing = {element.get("OID"): element for element in meta.findall(f"{{{ODM_NS}}}CodeList")}
    for oid in STANDARD_CODELISTS:
        if oid in existing:
            meta.remove(existing[oid])
    for oid, spec in STANDARD_CODELISTS.items():
        codelist = ET.SubElement(
            meta,
            f"{{{ODM_NS}}}CodeList",
            {
                "OID": oid,
                "Name": spec["name"],
                "DataType": "text",
                f"{{{DEF_NS}}}StandardOID": "STD.CT.ADAM.2025-03-28",
            },
        )
        for coded_value, decoded in spec["terms"]:
            term = ET.SubElement(codelist, f"{{{ODM_NS}}}EnumeratedItem", {"CodedValue": coded_value})
            decode = ET.SubElement(term, f"{{{ODM_NS}}}Decode")
            text = ET.SubElement(decode, f"{{{ODM_NS}}}TranslatedText")
            text.set(f"{{{XML_NS}}}lang", "en")
            text.text = decoded
    return len(STANDARD_CODELISTS)


def _insert_methods(meta: ET.Element) -> int:
    for child in list(meta):
        if child.tag == f"{{{ODM_NS}}}MethodDef" and (child.get("OID") or "").startswith("MT."):
            meta.remove(child)
    count = 0
    for dataset in DATASET_CLASSES:
        method = ET.SubElement(
            meta,
            f"{{{ODM_NS}}}MethodDef",
            {"OID": f"MT.{dataset}.DERIVED", "Name": f"{dataset} portfolio derivations", "Type": "Computation"},
        )
        _description(
            method,
            f"Controlled portfolio derivations for {dataset}; implementation is version-controlled in the repository and independently QCed by the clinical-programming workflow.",
            0,
        )
        count += 1
    return count


def _assert_structure(root: ET.Element, meta: ET.Element) -> dict[str, bool]:
    groups = meta.findall(f"{{{ODM_NS}}}ItemGroupDef")
    items = meta.findall(f"{{{ODM_NS}}}ItemDef")
    standards = meta.find(f"{{{DEF_NS}}}Standards")
    codelist_oids = {c.get("OID") for c in meta.findall(f"{{{ODM_NS}}}CodeList")}
    checks = {
        "context_other": root.get(f"{{{DEF_NS}}}Context") == "Other",
        "deprecated_standard_attrs_removed": (
            f"{{{DEF_NS}}}StandardName" not in meta.attrib
            and f"{{{DEF_NS}}}StandardVersion" not in meta.attrib
        ),
        "standards_present": standards is not None and len(list(standards)) >= 2,
        "dataset_descriptions_present": all(g.find(f"{{{ODM_NS}}}Description") is not None for g in groups),
        "dataset_classes_present": all(g.find(f"{{{DEF_NS}}}Class") is not None for g in groups),
        "dataset_is_nonstandard_absent": all(f"{{{DEF_NS}}}IsNonStandard" not in g.attrib for g in groups),
        "dataset_leaf_present": all(g.find(f"{{{DEF_NS}}}leaf") is not None for g in groups),
        "dataset_filename_matches_sas_name": all(
            Path(g.find(f"{{{DEF_NS}}}leaf").get(f"{{{XLINK_NS}}}href", "")).stem == g.get("SASDatasetName")
            for g in groups
        ),
        "deprecated_class_attribute_removed": all(f"{{{DEF_NS}}}Class" not in g.attrib for g in groups),
        "deprecated_keysequence_removed": all(
            f"{{{DEF_NS}}}KeySequence" not in ref.attrib
            for g in groups
            for ref in g.findall(f"{{{ODM_NS}}}ItemRef")
        ),
        "variable_descriptions_present": all(i.find(f"{{{ODM_NS}}}Description") is not None for i in items),
        "variable_origins_present": all(i.find(f"{{{DEF_NS}}}Origin") is not None for i in items),
        "sas_field_names_valid": all(0 < len(i.get("SASFieldName", "")) <= 8 for i in items),
        "numeric_lengths_present": all(
            i.get("DataType", "").lower() not in {"integer", "float"} or bool(i.get("Length")) for i in items
        ),
        "float_significant_digits_present": all(
            i.get("DataType", "").lower() != "float" or bool(i.get("SignificantDigits")) for i in items
        ),
        "standard_codelists_present": set(STANDARD_CODELISTS).issubset(codelist_oids),
        "referenced_codelists_resolve": all(
            ref.get("CodeListOID") in codelist_oids
            for item in items
            for ref in item.findall(f"{{{ODM_NS}}}CodeListRef")
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
    validation_aliases = _copy_validation_aliases(artifact_dir, source.parent, output_dir)

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
    codelist_count = _insert_codelists(meta)
    method_count = _insert_methods(meta)
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
        "round1_reference": {
            "pinnacle21_run_id": ROUND1_RUN_ID,
            "artifact_id": ROUND1_ARTIFACT_ID,
            "artifact_digest": ROUND1_ARTIFACT_DIGEST,
            "issue_classes": ROUND1_ISSUE_CLASSES,
            "occurrences": ROUND1_OCCURRENCES,
        },
        "baseline_define_sha256": baseline_sha,
        "remediated_define_sha256": _sha256(remediated_copy),
        "validation_dataset_aliases": validation_aliases,
        "targeted_findings": [
            "DD0052 SASDatasetName/ArchiveLocationID filename alignment",
            "DD0054 def:Class child metadata",
            "DD0072 variable-level Origin metadata with predecessor/derived lineage",
            "DD0120 removal of invalid IsNonStandard on standard datasets",
            "DD0124 standard codelists for AESER/AESEV/RACE/SEX",
            "DD0139 actual reference to ADaM controlled terminology standard",
        ],
        "known_not_remediated": [
            "TRTEMFL expects the standard CL.Y codelist, but the current controlled portfolio dataset contains explicit Y and N values. No CL.Y metadata is fabricated until the Python/SAS derivation policy is changed and re-reconciled."
        ],
        "group_changes": group_counts,
        "item_changes": item_counts,
        "standard_codelists_added": codelist_count,
        "method_defs_added": method_count,
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
