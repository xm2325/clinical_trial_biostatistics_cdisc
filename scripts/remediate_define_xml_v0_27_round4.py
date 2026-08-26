from __future__ import annotations

import argparse
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

ODM_NS = "http://www.cdisc.org/ns/odm/v1.3"
DEF_NS = "http://www.cdisc.org/ns/def/v2.1"

ET.register_namespace("", ODM_NS)
ET.register_namespace("def", DEF_NS)

ROUND3_RUN_ID = 32955862586
ROUND3_ARTIFACT_ID = 9602143224
ROUND3_ARTIFACT_DIGEST = "sha256:c7f13c9c5ed8cac2c88762443ca7ea8dafbb33db391a0a187b2b10b5c9463df9"
ROUND3_ISSUE_CLASSES = 1
ROUND3_OCCURRENCES = 1
Y_BLANK_CODELIST_OID = "CL.Y_BLANK"


def _add_y_blank_codelist(meta: ET.Element) -> None:
    for child in list(meta):
        if child.tag == f"{{{ODM_NS}}}CodeList" and child.get("OID") == Y_BLANK_CODELIST_OID:
            meta.remove(child)

    codelist = ET.Element(
        f"{{{ODM_NS}}}CodeList",
        {
            "OID": Y_BLANK_CODELIST_OID,
            "Name": "Y or blank analysis flag",
            "DataType": "text",
        },
    )
    ET.SubElement(codelist, f"{{{ODM_NS}}}EnumeratedItem", {"CodedValue": "Y"})

    children = list(meta)
    insert_at = next(
        (i for i, child in enumerate(children) if child.tag == f"{{{ODM_NS}}}MethodDef"),
        len(children),
    )
    meta.insert(insert_at, codelist)


def _link_trtemfl(meta: ET.Element) -> None:
    target = meta.find(f"{{{ODM_NS}}}ItemDef[@OID='IT.ADAE.TRTEMFL']")
    if target is None:
        raise RuntimeError("IT.ADAE.TRTEMFL not found")

    for ref in list(target.findall(f"{{{ODM_NS}}}CodeListRef")):
        target.remove(ref)

    ref = ET.Element(f"{{{ODM_NS}}}CodeListRef", {"CodeListOID": Y_BLANK_CODELIST_OID})
    children = list(target)
    origin_index = next(
        (i for i, child in enumerate(children) if child.tag == f"{{{DEF_NS}}}Origin"),
        len(children),
    )
    target.insert(origin_index, ref)


def _assert_round4(meta: ET.Element) -> dict[str, bool]:
    target = meta.find(f"{{{ODM_NS}}}ItemDef[@OID='IT.ADAE.TRTEMFL']")
    codelist = meta.find(f"{{{ODM_NS}}}CodeList[@OID='{Y_BLANK_CODELIST_OID}']")
    values = [] if codelist is None else [x.get("CodedValue") for x in codelist.findall(f"{{{ODM_NS}}}EnumeratedItem")]
    ref = None if target is None else target.find(f"{{{ODM_NS}}}CodeListRef")
    checks = {
        "trtemfl_item_present": target is not None,
        "trtemfl_codelist_ref_present": ref is not None and ref.get("CodeListOID") == Y_BLANK_CODELIST_OID,
        "y_blank_codelist_present": codelist is not None,
        "y_is_only_explicit_value": values == ["Y"],
        "codelist_is_sponsor_scoped": codelist is not None and f"{{{DEF_NS}}}StandardOID" not in codelist.attrib,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"Round-4 Define-XML assertions failed: {failed}")
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

    before = output_dir / "define_xml_candidate_v0_27_round3_before_yblank.xml"
    shutil.copy2(source, before)

    tree = ET.parse(source)
    root = tree.getroot()
    meta = root.find(f"{{{ODM_NS}}}Study/{{{ODM_NS}}}MetaDataVersion")
    if meta is None:
        raise SystemExit("MetaDataVersion not found")

    _add_y_blank_codelist(meta)
    _link_trtemfl(meta)
    checks = _assert_round4(meta)

    ET.indent(tree, space="  ")
    source.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n",
        encoding="utf-8",
        newline="\n",
    )
    final_copy = output_dir / "define_xml_candidate_v0_27_round4.xml"
    shutil.copy2(source, final_copy)

    manifest = {
        "version": "0.27.0-round4",
        "round3_reference": {
            "pinnacle21_run_id": ROUND3_RUN_ID,
            "artifact_id": ROUND3_ARTIFACT_ID,
            "artifact_digest": ROUND3_ARTIFACT_DIGEST,
            "issue_classes": ROUND3_ISSUE_CLASSES,
            "occurrences": ROUND3_OCCURRENCES,
            "residual_rule": "DD0124",
            "residual_variable": "TRTEMFL",
            "expected_standard_codelist_code": "CL.Y",
        },
        "remediation": "TRTEMFL data semantics changed coherently to Y/blank in Python and SAS; Define-XML now links TRTEMFL to a sponsor-scoped Y-only codelist rather than suppressing the validator finding.",
        "codelist_oid": Y_BLANK_CODELIST_OID,
        "structural_assertions": checks,
        "evidence_boundary": "A clean P21 report would remain public-data portfolio evidence only and would not establish formal ADaM conformance, GxP validation, or submission readiness.",
    }
    (output_dir / "define_xml_round4_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
