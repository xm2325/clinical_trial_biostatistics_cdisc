from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pandas as pd

VERSION = "0.26.0"
SAS_RUNTIME_STATUS = "NOT_EXECUTED_NO_SAS_RUNTIME"
P21_STATUS = "NOT_EXECUTED_NO_PINNACLE21_RUNTIME"
EVIDENCE_CLAIM = "PORTFOLIO_BMS_STATISTICAL_PROGRAMMING_EVIDENCE_READY"

ODM_NS = "http://www.cdisc.org/ns/odm/v1.3"
DEF_NS = "http://www.cdisc.org/ns/def/v2.1"
ET.register_namespace("", ODM_NS)
ET.register_namespace("def", DEF_NS)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _check(rows: list[dict[str, Any]], name: str, passed: bool, detail: str) -> None:
    rows.append({"check": name, "passed": bool(passed), "required": True, "detail": detail})


def _validate_config(cfg: dict[str, Any]) -> None:
    if cfg.get("version") != VERSION:
        raise ValueError(f"BMS evidence config must be version {VERSION}")
    if cfg.get("sas_runtime_status") != SAS_RUNTIME_STATUS:
        raise ValueError("SAS runtime status must remain explicitly unexecuted in this CI")
    if cfg.get("pinnacle21_status") != P21_STATUS:
        raise ValueError("Pinnacle 21 status must remain explicitly unexecuted in this CI")
    if cfg.get("evidence_claim") != EVIDENCE_CLAIM:
        raise ValueError("BMS evidence claim must remain portfolio-scoped")

    boundary = str(cfg.get("evidence_boundary", ""))
    required_boundary = [
        "no sponsor/CRO employment claim",
        "no executed SAS output in this CI",
        "no Pinnacle 21 execution",
        "no formal ADaM conformance",
        "no validated GxP environment",
        "not submission-ready",
    ]
    missing = [token for token in required_boundary if token not in boundary]
    if missing:
        raise ValueError(f"evidence boundary is incomplete: {missing}")

    programs = cfg.get("sas_programs")
    if not isinstance(programs, list) or len(programs) < 4:
        raise ValueError("v0.26 requires at least four controlled SAS source programs")
    ids = [str(row.get("id", "")) for row in programs]
    paths = [str(row.get("path", "")) for row in programs]
    if any(not item for item in ids + paths) or len(ids) != len(set(ids)) or len(paths) != len(set(paths)):
        raise ValueError("SAS program ids and paths must be non-empty and unique")
    roles = {str(row.get("role", "")) for row in programs}
    if "DERIVED_ANALYSIS_DATASET_STATIC_TRANSLATION" not in roles:
        raise ValueError("v0.26 must include SAS analysis-dataset derivation evidence")
    if not {"SAFETY_TFL_STATIC_TRANSLATION", "MMRM_TFL_STATIC_TRANSLATION"}.issubset(roles):
        raise ValueError("v0.26 must include representative SAS TFL evidence")

    datasets = cfg.get("analysis_datasets")
    if not isinstance(datasets, list) or len(datasets) != 4:
        raise ValueError("v0.26 controls exactly four representative analysis datasets")
    dataset_ids = [str(row.get("id", "")) for row in datasets]
    if len(dataset_ids) != len(set(dataset_ids)):
        raise ValueError("analysis dataset ids must be unique")
    for row in datasets:
        if not row.get("path") or not row.get("key") or not row.get("required_columns"):
            raise ValueError(f"analysis dataset contract incomplete: {row.get('id')}")

    handoff = cfg.get("pinnacle21_handoff")
    if not isinstance(handoff, list) or {row.get("dataset") for row in handoff} != set(dataset_ids):
        raise ValueError("Pinnacle 21 handoff must cover all controlled analysis datasets")
    if any(row.get("status") != P21_STATUS for row in handoff):
        raise ValueError("Pinnacle 21 handoff cannot imply execution")


def _review_sas(root: Path, cfg: dict[str, Any], checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prohibited = [_norm(item) for item in cfg.get("prohibited_claim_fragments", [])]
    rows: list[dict[str, Any]] = []

    for contract in cfg["sas_programs"]:
        path = root / contract["path"]
        exists = path.exists()
        _check(checks, f"SAS source exists: {contract['id']}", exists, contract["path"])
        if not exists:
            rows.append({
                "program_id": contract["id"], "role": contract["role"], "path": contract["path"],
                "sha256": "", "required_fragments": len(contract.get("required_fragments", [])),
                "matched_required_fragments": 0, "forbidden_hits": 0,
                "translation_basis": str(contract.get("translation_basis", "")),
                "runtime_status": SAS_RUNTIME_STATUS, "passed": False,
            })
            continue

        text = path.read_text(encoding="utf-8")
        normalised = _norm(text)
        required_raw = list(contract.get("required_fragments", []))
        required = [_norm(item) for item in required_raw]
        missing = [raw for raw, normed in zip(required_raw, required) if normed not in normalised]
        forbidden_raw = list(contract.get("forbidden_fragments", []))
        forbidden = [_norm(item) for item in forbidden_raw]
        forbidden_hits = [raw for raw, normed in zip(forbidden_raw, forbidden) if normed and normed in normalised]

        overclaim_hits = []
        for raw, normed in zip(cfg.get("prohibited_claim_fragments", []), prohibited):
            if not normed or normed not in normalised:
                continue
            if normed == "submission-ready" and ("not submission-ready" in normalised or "no claim of formal adam conformance" in normalised):
                continue
            if normed == "formal adam conformance" and ("not a claim of formal adam conformance" in normalised or "no formal adam conformance" in normalised):
                continue
            overclaim_hits.append(raw)

        status_ok = _norm(SAS_RUNTIME_STATUS) in normalised
        basis = str(contract.get("translation_basis", ""))
        basis_ok = True if not basis else (root / basis).exists()
        matched = len(required) - len(missing)
        passed = not missing and not forbidden_hits and not overclaim_hits and status_ok and basis_ok

        _check(checks, f"required SAS semantics: {contract['id']}", not missing,
               "missing=" + (" | ".join(missing) if missing else "0"))
        _check(checks, f"forbidden/overclaim SAS semantics absent: {contract['id']}",
               not forbidden_hits and not overclaim_hits,
               "hits=" + (" | ".join(forbidden_hits + overclaim_hits) if forbidden_hits or overclaim_hits else "0"))
        _check(checks, f"SAS runtime limitation explicit: {contract['id']}", status_ok, SAS_RUNTIME_STATUS)
        _check(checks, f"translation basis exists: {contract['id']}", basis_ok, basis or "not_applicable")

        rows.append({
            "program_id": contract["id"],
            "role": contract["role"],
            "path": contract["path"],
            "sha256": _sha256(path),
            "required_fragments": len(required),
            "matched_required_fragments": matched,
            "forbidden_hits": len(forbidden_hits) + len(overclaim_hits),
            "translation_basis": basis,
            "runtime_status": SAS_RUNTIME_STATUS,
            "passed": passed,
        })
    return rows


def _dataset_metadata(root: Path, cfg: dict[str, Any], checks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    datasets: list[dict[str, Any]] = []
    variables: list[dict[str, Any]] = []
    for contract in cfg["analysis_datasets"]:
        path = root / contract["path"]
        exists = path.exists()
        _check(checks, f"analysis dataset exists: {contract['id']}", exists, contract["path"])
        if not exists:
            continue
        frame = pd.read_csv(path)
        missing = [col for col in contract["required_columns"] if col not in frame.columns]
        _check(checks, f"required columns: {contract['id']}", not missing,
               "missing=" + (",".join(missing) if missing else "0"))
        key_cols = list(contract["key"])
        key_ok = all(col in frame.columns for col in key_cols)
        duplicates = int(frame.duplicated(key_cols).sum()) if key_ok else -1
        _check(checks, f"declared key unique: {contract['id']}", key_ok and duplicates == 0,
               f"key={'|'.join(key_cols)}; duplicates={duplicates}")
        datasets.append({"dataset":contract["id"],"label":contract["label"],"path":contract["path"],"rows":int(len(frame)),"columns":int(len(frame.columns)),"key":"|".join(key_cols),"repeating":contract["repeating"],"sha256":_sha256(path)})
        required_set=set(contract["required_columns"]); key_set=set(key_cols)
        for idx,col in enumerate(frame.columns,start=1):
            series=frame[col]
            variables.append({"dataset":contract["id"],"variable":col,"ordinal":idx,"pandas_dtype":str(series.dtype),"required_by_contract":col in required_set,"key_variable":col in key_set,"nonmissing_n":int(series.notna().sum()),"missing_n":int(series.isna().sum())})
    return datasets, variables


def _write_define_candidate(path: Path, dataset_rows: list[dict[str, Any]], variable_rows: list[dict[str, Any]]) -> dict[str,int]:
    by_dataset: dict[str,list[dict[str,Any]]] = {}
    for row in variable_rows: by_dataset.setdefault(str(row["dataset"]),[]).append(row)
    odm=ET.Element(f"{{{ODM_NS}}}ODM",{"ODMVersion":"1.3.2","FileType":"Snapshot","FileOID":"PORTFOLIO.V0.26.DEFINE.CANDIDATE","CreationDateTime":"2026-08-25T00:00:00Z"})
    study=ET.SubElement(odm,f"{{{ODM_NS}}}Study",{"OID":"PORTFOLIO.STUDY"})
    gv=ET.SubElement(study,f"{{{ODM_NS}}}GlobalVariables")
    ET.SubElement(gv,f"{{{ODM_NS}}}StudyName").text="Clinical Programming Portfolio"
    ET.SubElement(gv,f"{{{ODM_NS}}}StudyDescription").text="Portfolio metadata candidate only; not a regulatory submission artifact."
    ET.SubElement(gv,f"{{{ODM_NS}}}ProtocolName").text="PORTFOLIO"
    meta=ET.SubElement(study,f"{{{ODM_NS}}}MetaDataVersion",{"OID":"MDV.PORTFOLIO.V0.26","Name":"Portfolio Define-XML 2.1-shaped candidate",f"{{{DEF_NS}}}DefineVersion":"2.1.11",f"{{{DEF_NS}}}StandardName":"ADaM",f"{{{DEF_NS}}}StandardVersion":"1.3"})
    for ds in dataset_rows:
        ig=ET.SubElement(meta,f"{{{ODM_NS}}}ItemGroupDef",{"OID":f"IG.{ds['dataset']}","Name":str(ds["dataset"]),"Repeating":str(ds["repeating"]),"IsReferenceData":"No","SASDatasetName":str(ds["dataset"]),f"{{{DEF_NS}}}Structure":str(ds["label"]),f"{{{DEF_NS}}}Class":"PORTFOLIO ANALYSIS",f"{{{DEF_NS}}}ArchiveLocationID":f"LF.{ds['dataset']}"})
        for var in by_dataset.get(str(ds["dataset"]),[]):
            ET.SubElement(ig,f"{{{ODM_NS}}}ItemRef",{"ItemOID":f"IT.{ds['dataset']}.{var['variable']}","OrderNumber":str(var["ordinal"]),"Mandatory":"Yes" if bool(var["required_by_contract"]) else "No",f"{{{DEF_NS}}}KeySequence":str(var["ordinal"]) if bool(var["key_variable"]) else ""})
    for ds in dataset_rows:
        for var in by_dataset.get(str(ds["dataset"]),[]):
            dtype=str(var["pandas_dtype"]).lower(); data_type="integer" if "int" in dtype else "float" if "float" in dtype else "text"
            attrs={"OID":f"IT.{ds['dataset']}.{var['variable']}","Name":str(var["variable"]),"SASFieldName":str(var["variable"]),"DataType":data_type}
            if data_type=="text": attrs["Length"]="200"
            ET.SubElement(meta,f"{{{ODM_NS}}}ItemDef",attrs)
    tree=ET.ElementTree(odm); ET.indent(tree,space="  "); tree.write(path,encoding="utf-8",xml_declaration=True); ET.parse(path)
    return {"datasets":len(dataset_rows),"variables":len(variable_rows)}


def _write_execution_contract(path:Path,cfg:dict[str,Any])->int:
    rows=[{**item,"runtime_status":SAS_RUNTIME_STATUS,"execution_result":"NOT_RUN","comparison_result":"NOT_RUN","evidence_boundary":"External licensed SAS runtime required before execution/comparison claims."} for item in cfg["external_sas_reconciliation"]]
    pd.DataFrame(rows).to_csv(path,index=False); return len(rows)


def _write_p21_handoff(path:Path,cfg:dict[str,Any])->int:
    rows=[{**item,"validation_result":"NOT_RUN","report_path":"","evidence_boundary":"Pinnacle 21 runtime not available in this CI; this is a controlled handoff only."} for item in cfg["pinnacle21_handoff"]]
    pd.DataFrame(rows).to_csv(path,index=False); return len(rows)


def assess_bms_statistical_programming(root:Path):
    root=Path(root); cfg=_load_json(root/"spec"/"bms_statistical_programming_v0_26.json"); _validate_config(cfg); checks=[]
    v025_path=root/"outputs"/"clinical_programming_workflow_metrics.json"; v025_exists=v025_path.exists(); _check(checks,"v0.25 clinical-programming metrics exist",v025_exists,str(v025_path.relative_to(root)))
    v025_passed=bool(_load_json(v025_path).get("all_required_passed")) if v025_exists else False; _check(checks,"v0.25 clinical-programming release gate passed",v025_passed,f"all_required_passed={v025_passed}")
    for contract in cfg["source_inputs"]:
        path=root/contract["path"]; exists=path.exists(); _check(checks,f"SAS source input exists: {contract['id']}",exists,contract["path"])
        if exists:
            frame=pd.read_csv(path,nrows=5); missing=[c for c in contract["required_columns"] if c not in frame.columns]; _check(checks,f"SAS source schema: {contract['id']}",not missing,"missing="+(",".join(missing) if missing else "0"))
    sas_rows=_review_sas(root,cfg,checks); dataset_rows,variable_rows=_dataset_metadata(root,cfg,checks)
    outputs=root/"outputs"; outputs.mkdir(parents=True,exist_ok=True)
    ddt_path=outputs/"analysis_data_definition_table_v0_26.csv"; pd.DataFrame(variable_rows).to_csv(ddt_path,index=False); _check(checks,"Data Definition Table generated",ddt_path.exists() and bool(variable_rows),f"dataset_variables={len(variable_rows)}")
    define_path=outputs/"define_xml_candidate_v0_26.xml"; define_counts=_write_define_candidate(define_path,dataset_rows,variable_rows); ET.parse(define_path); _check(checks,"Define-XML 2.1-shaped candidate is well formed",define_path.exists(),f"datasets={define_counts['datasets']}; variables={define_counts['variables']}")
    execution_contract_path=outputs/"sas_external_execution_contract.csv"; execution_rows=_write_execution_contract(execution_contract_path,cfg); _check(checks,"external SAS reconciliation contract generated",execution_rows==len(cfg["external_sas_reconciliation"]),f"rows={execution_rows}")
    p21_path=outputs/"pinnacle21_handoff_v0_26.csv"; p21_rows=_write_p21_handoff(p21_path,cfg); _check(checks,"Pinnacle 21 handoff covers all controlled datasets",p21_rows==len(cfg["analysis_datasets"]),f"rows={p21_rows}; status={P21_STATUS}")
    external_outputs_absent=all(not (root/row["expected_external_output"]).exists() for row in cfg["external_sas_reconciliation"]); _check(checks,"CI does not misrepresent external SAS outputs as executed",external_outputs_absent,f"runtime_status={SAS_RUNTIME_STATUS}")
    claim_text=" ".join([cfg["evidence_claim"],cfg["evidence_boundary"],cfg["sas_runtime_status"],cfg["pinnacle21_status"]]).lower(); dangerous=[("sas runtime success","no sas runtime success"),("pinnacle 21 passed","pinnacle 21 not executed"),("validated gxp environment","no validated gxp environment"),("sponsor/cro production experience","no sponsor/cro production experience")]; overclaims=[token for token,negated in dangerous if token in claim_text and negated not in claim_text]; _check(checks,"controlled evidence boundary contains no positive production/submission overclaim",not overclaims,"hits="+("|".join(overclaims) if overclaims else "0"))
    required_checks=sum(bool(r["required"]) for r in checks); required_passed=sum(bool(r["required"] and r["passed"]) for r in checks); all_passed=required_checks==required_passed
    metrics={"version":VERSION,"target_role":cfg["target_role"],"sas_runtime_status":SAS_RUNTIME_STATUS,"pinnacle21_status":P21_STATUS,"sas_runtime_executed":False,"pinnacle21_executed":False,"controlled_claim":EVIDENCE_CLAIM if all_passed else "","sas_programs":len(sas_rows),"sas_programs_static_review_passed":sum(bool(r["passed"]) for r in sas_rows),"analysis_datasets":len(dataset_rows),"analysis_dataset_variables":len(variable_rows),"external_sas_reconciliation_rows":execution_rows,"pinnacle21_handoff_rows":p21_rows,"define_xml_candidate_datasets":define_counts["datasets"],"define_xml_candidate_variables":define_counts["variables"],"required_checks":required_checks,"required_checks_passed":required_passed,"all_required_passed":all_passed,"evidence_boundary":cfg["evidence_boundary"]}
    return sas_rows,dataset_rows,variable_rows,checks,metrics


def write_bms_statistical_programming_outputs(root:Path)->dict[str,Any]:
    root=Path(root); sas_rows,dataset_rows,variable_rows,checks,metrics=assess_bms_statistical_programming(root); outputs=root/"outputs"
    pd.DataFrame(sas_rows).to_csv(outputs/"bms_sas_static_review_v0_26.csv",index=False); pd.DataFrame(dataset_rows).to_csv(outputs/"bms_analysis_dataset_inventory_v0_26.csv",index=False); pd.DataFrame(checks).to_csv(outputs/"bms_statistical_programming_qc_v0_26.csv",index=False); (outputs/"bms_statistical_programming_metrics_v0_26.json").write_text(json.dumps(metrics,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    artifact_paths=[outputs/"analysis_data_definition_table_v0_26.csv",outputs/"define_xml_candidate_v0_26.xml",outputs/"sas_external_execution_contract.csv",outputs/"pinnacle21_handoff_v0_26.csv",outputs/"bms_sas_static_review_v0_26.csv",outputs/"bms_analysis_dataset_inventory_v0_26.csv",outputs/"bms_statistical_programming_qc_v0_26.csv",outputs/"bms_statistical_programming_metrics_v0_26.json"]
    manifest_rows=[{"artifact":str(path.relative_to(root)),"sha256":_sha256(path),"bytes":path.stat().st_size} for path in artifact_paths]; pd.DataFrame(manifest_rows).to_csv(outputs/"bms_submission_artifact_manifest_v0_26.csv",index=False)
    lines=["# v0.26 BMS statistical-programming evidence summary","",f"- target role: **{metrics['target_role']}**",f"- SAS source programs statically reviewed: **{metrics['sas_programs_static_review_passed']}/{metrics['sas_programs']}**",f"- controlled analysis datasets: **{metrics['analysis_datasets']}**",f"- analysis-data definition rows: **{metrics['analysis_dataset_variables']}**",f"- Define-XML 2.1-shaped candidate: **{metrics['define_xml_candidate_datasets']} datasets / {metrics['define_xml_candidate_variables']} variables**",f"- external SAS reconciliation rows: **{metrics['external_sas_reconciliation_rows']}**",f"- Pinnacle 21 handoff rows: **{metrics['pinnacle21_handoff_rows']}**",f"- required checks: **{metrics['required_checks_passed']}/{metrics['required_checks']}**",f"- SAS runtime status: **{metrics['sas_runtime_status']}**",f"- Pinnacle 21 status: **{metrics['pinnacle21_status']}**",f"- controlled claim: **`{metrics['controlled_claim']}`**","","## Evidence boundary","",metrics["evidence_boundary"],"","The XML file is a portfolio metadata candidate shaped around Define-XML 2.1 concepts; it is deliberately not described as a validated regulatory submission artefact. Pinnacle 21 and licensed SAS execution remain controlled external-runtime handoffs."]
    (outputs/"bms_statistical_programming_summary_v0_26.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    if not metrics["all_required_passed"]: raise RuntimeError("v0.26 BMS statistical-programming evidence gate failed")
    return metrics
