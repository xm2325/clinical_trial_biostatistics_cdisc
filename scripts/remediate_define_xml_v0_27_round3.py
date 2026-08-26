from __future__ import annotations

import argparse
import json
import re
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

ROUND2_RUN_ID = 32946093763
ROUND2_ARTIFACT_ID = 9598494942
ROUND2_ARTIFACT_DIGEST = "sha256:2e2d74d645c57f06d9b6b48fe0d57116c2073d6e3801b6ee366973eac4abf8ad"
ROUND2_ISSUE_CLASSES = 8
ROUND2_OCCURRENCES = 97

CT_STANDARD_OID = "STD.CT.SDTM.2025-03-28"

PREDECESSOR_SOURCE = {
    ("ADSL", "STUDYID"): "DM.STUDYID",
    ("ADSL", "USUBJID"): "DM.USUBJID",
    ("ADSL", "AGE"): "DM.AGE",
    ("ADSL", "SEX"): "DM.SEX",
    ("ADSL", "RACE"): "DM.RACE",
    ("ADSL", "COUNTRY"): "DM.COUNTRY",
    ("ADSL", "TRT01P"): "DM.ARM",
    ("ADSL", "TRT01A"): "DM.ACTARM",
    ("ADAE", "STUDYID"): "AE.STUDYID",
    ("ADAE", "USUBJID"): "AE.USUBJID",
    ("ADAE", "AESEQ"): "AE.AESEQ",
    ("ADAE", "AETERM"): "AE.AETERM",
    ("ADAE", "AEDECOD"): "AE.AEDECOD",
    ("ADAE", "AEBODSYS"): "AE.AEBODSYS",
    ("ADAE", "AESEV"): "AE.AESEV",
    ("ADAE", "AESER"): "AE.AESER",
    ("ADAE", "AEREL"): "AE.AEREL",
    ("ADAE", "AEOUT"): "AE.AEOUT",
    ("ADAE", "TRT01A"): "ADSL.TRT01A",
    ("ADAE", "TRTSDT"): "ADSL.TRTSDT",
    ("ADAE", "TRTEDT"): "ADSL.TRTEDT",
    ("ADAE", "SAFFL"): "ADSL.SAFFL",
    ("ADQS", "STUDYID"): "QS.STUDYID",
    ("ADQS", "USUBJID"): "QS.USUBJID",
    ("ADQS", "QSSEQ"): "QS.QSSEQ",
    ("ADTTE", "STUDYID"): "ADSL.STUDYID",
    ("ADTTE", "USUBJID"): "ADSL.USUBJID",
    ("ADTTE", "TRT01P"): "ADSL.TRT01P",
    ("ADTTE", "TRT01A"): "ADSL.TRT01A",
    ("ADTTE", "SAFFL"): "ADSL.SAFFL",
}

CODELISTS = {
    "CL.NY": {
        "name": "No Yes Response",
        "nci": "C66742",
        "terms": [("N", "C49487"), ("Y", "C49488")],
    },
    "CL.AESEV": {
        "name": "Severity/Intensity Scale for Adverse Events",
        "nci": "C66769",
        "terms": [("MILD", "C41338"), ("MODERATE", "C41339"), ("SEVERE", "C41340")],
    },
    "CL.RACE": {
        "name": "Race",
        "nci": "C74457",
        "terms": [
            ("AMERICAN INDIAN OR ALASKA NATIVE", "C41259"),
            ("ASIAN", "C41260"),
            ("BLACK OR AFRICAN AMERICAN", "C16352"),
            ("WHITE", "C41261"),
        ],
    },
    "CL.SEX": {
        "name": "Sex",
        "nci": "C66731",
        "terms": [("F", "C16576"), ("M", "C20197")],
    },
}


def _translated_text(parent: ET.Element, text: str) -> None:
    for child in list(parent):
        parent.remove(child)
    desc = ET.SubElement(parent, f"{{{ODM_NS}}}Description")
    translated = ET.SubElement(desc, f"{{{ODM_NS}}}TranslatedText")
    translated.set(f"{{{XML_NS}}}lang", "en")
    translated.text = text


def _fix_standards(meta: ET.Element) -> int:
    standards = meta.find(f"{{{DEF_NS}}}Standards")
    if standards is None:
        raise RuntimeError("def:Standards is missing")
    removed = 0
    for standard in list(standards):
        if standard.tag == f"{{{DEF_NS}}}Standard" and standard.get("Type") == "CT":
            standards.remove(standard)
            removed += 1
    ET.SubElement(
        standards,
        f"{{{DEF_NS}}}Standard",
        {
            "OID": CT_STANDARD_OID,
            "Name": "CDISC/NCI",
            "Type": "CT",
            "PublishingSet": "SDTM",
            "Version": "2025-03-28",
            "Status": "Final",
        },
    )
    return removed


def _move_classes(meta: ET.Element) -> int:
    moved = 0
    for group in meta.findall(f"{{{ODM_NS}}}ItemGroupDef"):
        klass = group.find(f"{{{DEF_NS}}}Class")
        if klass is None:
            continue
        group.remove(klass)
        children = list(group)
        leaf_index = next((i for i, child in enumerate(children) if child.tag == f"{{{DEF_NS}}}leaf"), len(children))
        group.insert(leaf_index, klass)
        moved += 1
    return moved


def _fix_origins(meta: ET.Element) -> tuple[int, int]:
    predecessors = 0
    derived = 0
    for item in meta.findall(f"{{{ODM_NS}}}ItemDef"):
        oid = item.get("OID", "")
        parts = oid.split(".")
        if len(parts) < 3:
            continue
        dataset = parts[1]
        variable = item.get("Name", parts[-1])
        origin = item.find(f"{{{DEF_NS}}}Origin")
        if origin is None:
            continue
        origin_type = origin.get("Type")
        if origin_type == "Predecessor":
            source = PREDECESSOR_SOURCE.get((dataset, variable))
            if not source:
                raise RuntimeError(f"Missing exact predecessor source for {dataset}.{variable}")
            origin.attrib.pop("Source", None)
            _translated_text(origin, source)
            predecessors += 1
        elif origin_type in {"Derived", "Assigned"}:
            origin.set("Source", "Sponsor")
            derived += 1
    return predecessors, derived


def _rebuild_codelists(meta: ET.Element) -> int:
    children = list(meta)
    positions = [i for i, child in enumerate(children) if child.tag == f"{{{ODM_NS}}}CodeList"]
    insert_at = min(positions) if positions else next(
        (i for i, child in enumerate(children) if child.tag == f"{{{ODM_NS}}}MethodDef"), len(children)
    )
    for child in list(meta):
        if child.tag == f"{{{ODM_NS}}}CodeList" and child.get("OID") in CODELISTS:
            meta.remove(child)

    added = 0
    for offset, (oid, spec) in enumerate(CODELISTS.items()):
        codelist = ET.Element(
            f"{{{ODM_NS}}}CodeList",
            {
                "OID": oid,
                "Name": spec["name"],
                "DataType": "text",
                f"{{{DEF_NS}}}StandardOID": CT_STANDARD_OID,
            },
        )
        for coded_value, nci_code in spec["terms"]:
            item = ET.SubElement(codelist, f"{{{ODM_NS}}}EnumeratedItem", {"CodedValue": coded_value})
            ET.SubElement(item, f"{{{ODM_NS}}}Alias", {"Name": nci_code, "Context": "nci:ExtCodeID"})
        ET.SubElement(codelist, f"{{{ODM_NS}}}Alias", {"Name": spec["nci"], "Context": "nci:ExtCodeID"})
        meta.insert(insert_at + offset, codelist)
        added += 1
    return added


def _assert_round3(meta: ET.Element) -> dict[str, bool]:
    groups = meta.findall(f"{{{ODM_NS}}}ItemGroupDef")
    predecessor_origins = []
    for item in meta.findall(f"{{{ODM_NS}}}ItemDef"):
        origin = item.find(f"{{{DEF_NS}}}Origin")
        if origin is not None and origin.get("Type") == "Predecessor":
            text = origin.findtext(f"{{{ODM_NS}}}Description/{{{ODM_NS}}}TranslatedText", default="")
            predecessor_origins.append((origin, text))

    standards = meta.find(f"{{{DEF_NS}}}Standards")
    ct = [] if standards is None else [s for s in standards if s.get("Type") == "CT"]
    codelists = {c.get("OID"): c for c in meta.findall(f"{{{ODM_NS}}}CodeList")}

    checks = {
        "class_after_itemrefs": all(
            (lambda children: (
                next(i for i, c in enumerate(children) if c.tag == f"{{{DEF_NS}}}Class")
                > max(i for i, c in enumerate(children) if c.tag == f"{{{ODM_NS}}}ItemRef")
            ))(list(group))
            for group in groups
        ),
        "predecessor_source_attribute_absent": all("Source" not in origin.attrib for origin, _ in predecessor_origins),
        "predecessor_syntax_exact": all(re.fullmatch(r"[A-Z0-9_]+\.[A-Z0-9_]+", text or "") for _, text in predecessor_origins),
        "ct_standard_is_cdisc_nci_sdtm": len(ct) == 1 and ct[0].get("Name") == "CDISC/NCI" and ct[0].get("PublishingSet") == "SDTM",
        "controlled_codelists_present": set(CODELISTS).issubset(codelists),
        "codelist_aliases_present": all(codelists[oid].find(f"{{{ODM_NS}}}Alias") is not None for oid in CODELISTS),
        "enumerated_items_have_alias_not_decode": all(
            all(
                term.find(f"{{{ODM_NS}}}Alias") is not None and term.find(f"{{{ODM_NS}}}Decode") is None
                for term in codelists[oid].findall(f"{{{ODM_NS}}}EnumeratedItem")
            )
            for oid in CODELISTS
        ),
        "codelists_reference_ct_standard": all(codelists[oid].get(f"{{{DEF_NS}}}StandardOID") == CT_STANDARD_OID for oid in CODELISTS),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"Round-3 Define-XML assertions failed: {failed}")
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
        raise SystemExit("Remediated Define-XML source not found")

    before = output_dir / "define_xml_candidate_v0_27_round2.xml"
    shutil.copy2(source, before)

    tree = ET.parse(source)
    root = tree.getroot()
    meta = root.find(f"{{{ODM_NS}}}Study/{{{ODM_NS}}}MetaDataVersion")
    if meta is None:
        raise SystemExit("MetaDataVersion not found")

    removed_ct = _fix_standards(meta)
    classes_moved = _move_classes(meta)
    predecessors, derived = _fix_origins(meta)
    codelists = _rebuild_codelists(meta)
    checks = _assert_round3(meta)

    ET.indent(tree, space="  ")
    body = ET.tostring(root, encoding="unicode")
    source.write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + body + "\n", encoding="utf-8", newline="\n")
    final_copy = output_dir / "define_xml_candidate_v0_27_round3.xml"
    shutil.copy2(source, final_copy)

    manifest = {
        "version": "0.27.0-round3",
        "round2_reference": {
            "pinnacle21_run_id": ROUND2_RUN_ID,
            "artifact_id": ROUND2_ARTIFACT_ID,
            "artifact_digest": ROUND2_ARTIFACT_DIGEST,
            "issue_classes": ROUND2_ISSUE_CLASSES,
            "occurrences": ROUND2_OCCURRENCES,
        },
        "targeted_rules": ["DD0001", "DD0003", "DD0007", "DD0021", "DD0129", "DD0148"],
        "ct_standards_replaced": removed_ct,
        "dataset_classes_relocated": classes_moved,
        "predecessor_origins_rewritten": predecessors,
        "derived_origins_confirmed": derived,
        "standard_codelists_rebuilt": codelists,
        "structural_assertions": checks,
        "known_residual": "DD0124 TRTEMFL / CL.Y remains intentionally unresolved because the controlled dataset contains explicit Y and N. Fixing it requires a coordinated Python/SAS derivation change and re-reconciliation, not metadata-only suppression.",
        "evidence_boundary": "Round-3 remediation is driven by real P21 Community findings; it does not claim formal ADaM conformance, GxP validation, or submission readiness.",
    }
    (output_dir / "define_xml_round3_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
