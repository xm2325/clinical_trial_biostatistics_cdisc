from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import pandas as pd

VERSION = "0.18.0"
REF_RE = re.compile(r"^[A-Z][A-Z0-9_]*\.[A-Z][A-Z0-9_]*$")
RAW_DOMAINS = {"DM", "EX", "DS", "AE", "QS", "SPEC"}

DATASETS = {
    "ADSL_STYLE": {
        "alias": "ADSL", "file": "outputs/adsl_style.csv", "label": "Subject-Level Analysis Dataset Style",
        "class": "SUBJECT LEVEL ANALYSIS DATASET STYLE", "keys": ["STUDYID", "USUBJID"],
        "columns": ["STUDYID","USUBJID","AGE","SEX","RACE","COUNTRY","TRT01P","TRT01A","TRTSDT","TRTEDT","TRTSDTSRC","TRTEDTSRC","TRTSDT_DM","TRTEDT_DM","EXDURN_RAW","TRTDURN","EXN","EXTRTS","EXDOSE_MAX","EXDOSE_MEAN","RANDFL","SAFFL","COMPLFL","DCSFL","EOSDECOD","EOSTERM","EOSDT"],
    },
    "ADAE_STYLE": {
        "alias": "ADAE", "file": "outputs/adae_style.csv", "label": "Adverse Event Analysis Dataset Style",
        "class": "OCCURRENCE DATA STRUCTURE STYLE", "keys": ["STUDYID", "USUBJID", "AESEQ"],
        "columns": ["STUDYID","USUBJID","AESEQ","AETERM","AEDECOD","AEBODSYS","AESEV","AESER","AEREL","AEOUT","ASTDT","AENDT","ASTDY","TRT01A","TRTSDT","TRTEDT","SAFFL","TRTEMFL","RELFL","MODSEVFL"],
    },
    "ADQS_ACTOT_STYLE": {
        "alias": "ADQS", "file": "outputs/adqs_actot_style.csv", "label": "ACTOT Questionnaire Analysis Dataset Style",
        "class": "BASIC DATA STRUCTURE STYLE", "keys": ["STUDYID", "USUBJID", "QSSEQ"],
        "columns": ["STUDYID","USUBJID","TRT01A","PARAMCD","PARAM","AVISIT","AVISITN","ADY","ADT","AVAL","BASE","CHG","ABLFL","EFFFL","QSSEQ"],
    },
    "ADTTE_RETENTION_STYLE": {
        "alias": "ADTTE", "file": "outputs/adtte_retention_style.csv", "label": "Study-Retention Time-to-Event Analysis Dataset Style",
        "class": "TIME-TO-EVENT BASIC DATA STRUCTURE STYLE", "keys": ["STUDYID", "USUBJID", "PARAMCD"],
        "columns": ["STUDYID","USUBJID","TRT01P","TRT01A","ANLTRT","ANLTRTSRC","TRTDIFFL","SAFFL","PARAM","PARAMCD","STARTDT","ADT","AVAL","CNSR","EVNTDESC","DCSREAS","ANL01FL","SRCDOM","SRCVAR","STARTSRC","ADTSRC","CNSRSRC","EVNTSRC"],
    },
}

LABELS = {
    "STUDYID":"Study Identifier","USUBJID":"Unique Subject Identifier","TRT01P":"Planned Treatment for Period 01","TRT01A":"Actual Treatment for Period 01",
    "TRTSDT":"Date of First Exposure to Treatment","TRTEDT":"Date of Last Exposure to Treatment","RANDFL":"Randomised Population Flag","SAFFL":"Safety Population Flag",
    "COMPLFL":"Study Completion Flag","DCSFL":"Study Discontinuation Flag","PARAMCD":"Parameter Code","PARAM":"Parameter Description","AVISIT":"Analysis Visit",
    "AVISITN":"Analysis Visit Number","ADY":"Analysis Relative Day","ADT":"Analysis Date","AVAL":"Analysis Value","BASE":"Baseline Value","CHG":"Change from Baseline",
    "ABLFL":"Baseline Record Flag","EFFFL":"Efficacy Population Flag","ANLTRT":"Analysis Treatment","ANLTRTSRC":"Analysis Treatment Source",
    "TRTDIFFL":"Planned/Actual Treatment Difference Flag","STARTDT":"Time-to-Event Origin Date","CNSR":"Censoring Indicator","EVNTDESC":"Event or Censor Description",
    "DCSREAS":"Discontinuation Reason","ANL01FL":"Primary Analysis Record Flag","SRCDOM":"Source Domain","SRCVAR":"Source Variable","STARTSRC":"Origin-Date Source",
    "ADTSRC":"Analysis-Date Source","CNSRSRC":"Censoring-Status Source","EVNTSRC":"Event-Description Source",
}

ADSL_SOURCES = {
    "STUDYID":["DM.STUDYID"],"USUBJID":["DM.USUBJID"],"AGE":["DM.AGE"],"SEX":["DM.SEX"],"RACE":["DM.RACE"],"COUNTRY":["DM.COUNTRY"],
    "TRT01P":["DM.ARM"],"TRT01A":["DM.ACTARM"],"TRTSDT":["EX.EXSTDTC","DM.RFXSTDTC"],"TRTEDT":["EX.EXENDTC","DM.RFXENDTC","DS.DSSTDTC"],
    "TRTSDTSRC":["EX.EXSTDTC","DM.RFXSTDTC"],"TRTEDTSRC":["EX.EXENDTC","DM.RFXENDTC","DS.DSSTDTC"],"TRTSDT_DM":["DM.RFXSTDTC"],"TRTEDT_DM":["DM.RFXENDTC"],
    "EXDURN_RAW":["EX.EXSTDTC","EX.EXENDTC"],"TRTDURN":["ADSL.TRTSDT","ADSL.TRTEDT"],"EXN":["EX.EXSEQ"],"EXTRTS":["EX.EXTRT"],
    "EXDOSE_MAX":["EX.EXDOSE"],"EXDOSE_MEAN":["EX.EXDOSE"],"RANDFL":["DS.DSDECOD"],"SAFFL":["EX.EXSEQ"],"COMPLFL":["DS.DSDECOD"],
    "DCSFL":["ADSL.RANDFL","ADSL.COMPLFL"],"EOSDECOD":["DS.DSDECOD"],"EOSTERM":["DS.DSTERM"],"EOSDT":["DS.DSSTDTC"],
}
ADAE_SOURCES = {v:[f"AE.{v}"] for v in ["STUDYID","USUBJID","AESEQ","AETERM","AEDECOD","AEBODSYS","AESEV","AESER","AEREL","AEOUT"]}
ADAE_SOURCES.update({"ASTDT":["AE.AESTDTC"],"AENDT":["AE.AEENDTC"],"ASTDY":["AE.AESTDY","AE.AESTDTC","ADSL.TRTSDT"],"TRT01A":["ADSL.TRT01A"],"TRTSDT":["ADSL.TRTSDT"],"TRTEDT":["ADSL.TRTEDT"],"SAFFL":["ADSL.SAFFL"],"TRTEMFL":["AE.AESTDTC","ADSL.TRTSDT","ADSL.TRTEDT","ADSL.SAFFL"],"RELFL":["AE.AEREL"],"MODSEVFL":["AE.AESEV"]})
ADQS_SOURCES = {"STUDYID":["QS.STUDYID"],"USUBJID":["QS.USUBJID"],"TRT01A":["ADSL.TRT01A"],"PARAMCD":["QS.QSTESTCD"],"PARAM":["QS.QSTEST"],"AVISIT":["QS.VISIT"],"AVISITN":["QS.VISITNUM"],"ADY":["QS.QSDY"],"ADT":["QS.QSDTC"],"AVAL":["QS.QSSTRESN"],"BASE":["QS.QSSTRESN","QS.QSBLFL"],"CHG":["ADQS.AVAL","ADQS.BASE"],"ABLFL":["QS.QSBLFL"],"EFFFL":["ADQS.BASE","ADQS.AVAL"],"QSSEQ":["QS.QSSEQ"]}
ADTTE_SOURCES = {"STUDYID":["ADSL.STUDYID"],"USUBJID":["ADSL.USUBJID"],"TRT01P":["ADSL.TRT01P"],"TRT01A":["ADSL.TRT01A"],"ANLTRT":["ADSL.TRT01P"],"ANLTRTSRC":["ADSL.TRT01P"],"TRTDIFFL":["ADSL.TRT01P","ADSL.TRT01A"],"SAFFL":["ADSL.SAFFL"],"PARAM":["SPEC.TTDISC_PARAMETER"],"PARAMCD":["SPEC.TTDISC_PARAMETER"],"STARTDT":["ADSL.TRTSDT"],"ADT":["ADSL.EOSDT"],"AVAL":["ADSL.TRTSDT","ADSL.EOSDT"],"CNSR":["ADSL.DCSFL","ADSL.COMPLFL"],"EVNTDESC":["ADSL.EOSDECOD","ADSL.EOSTERM","SPEC.CENSOR_RULE"],"DCSREAS":["ADSL.EOSDECOD","ADSL.EOSTERM"],"ANL01FL":["SPEC.ANALYSIS_FLAG"],"SRCDOM":["SPEC.SOURCE_DOMAIN"],"SRCVAR":["SPEC.EVENT_OR_CENSOR_VARIABLE"],"STARTSRC":["SPEC.ORIGIN_VARIABLE"],"ADTSRC":["SPEC.EVENT_OR_CENSOR_VARIABLE"],"CNSRSRC":["ADSL.DCSFL","ADSL.COMPLFL"],"EVNTSRC":["ADSL.EOSDECOD","SPEC.CENSOR_RULE"]}
SOURCES = {"ADSL_STYLE":ADSL_SOURCES,"ADAE_STYLE":ADAE_SOURCES,"ADQS_ACTOT_STYLE":ADQS_SOURCES,"ADTTE_RETENTION_STYLE":ADTTE_SOURCES}

PREDECESSOR = {
    "ADSL_STYLE": {"STUDYID","USUBJID","AGE","SEX","RACE","COUNTRY","TRT01P","TRT01A","TRTSDT_DM","TRTEDT_DM"},
    "ADAE_STYLE": {"STUDYID","USUBJID","AESEQ","AETERM","AEDECOD","AEBODSYS","AESEV","AESER","AEREL","AEOUT","TRT01A","TRTSDT","TRTEDT","SAFFL"},
    "ADQS_ACTOT_STYLE": {"STUDYID","USUBJID","TRT01A","QSSEQ"},
    "ADTTE_RETENTION_STYLE": {"STUDYID","USUBJID","TRT01P","TRT01A","SAFFL"},
}
NUMERIC = {"AGE","EXDURN_RAW","TRTDURN","EXN","EXDOSE_MAX","EXDOSE_MEAN","AESEQ","ASTDY","AVISITN","ADY","AVAL","BASE","CHG","QSSEQ","CNSR"}
DATES = {"TRTSDT","TRTEDT","TRTSDT_DM","TRTEDT_DM","EOSDT","ASTDT","AENDT","ADT","STARTDT"}
TRACE = {"TRTSDTSRC","TRTEDTSRC","ANLTRTSRC","SRCDOM","SRCVAR","STARTSRC","ADTSRC","CNSRSRC","EVNTSRC"}

DERIVATION = {
    "TRTSDT":"Earliest observed EX start date; DM RFXSTDTC is the fallback.","TRTEDT":"Latest observed EX end date; DM RFXENDTC then final DS disposition date are ordered fallbacks.",
    "TRTDURN":"TRTEDT - TRTSDT + 1 for a valid treatment window.","RANDFL":"Y when DS contains a RANDOMIZED record, else N.","SAFFL":"Y when at least one observed EX record exists, else N.",
    "DCSFL":"Y for randomized subjects not marked completed, else N.","TRTEMFL":"Y when AE starts on/after TRTSDT and no later than TRTEDT + 30 days for safety-population subjects.",
    "RELFL":"Y when AEREL is POSSIBLE, PROBABLE, DEFINITE or RELATED.","MODSEVFL":"Y when AESEV is MODERATE or SEVERE.","BASE":"Last ACTOT record flagged QSBLFL=Y for the subject.",
    "CHG":"0 for baseline records; otherwise AVAL - BASE.","EFFFL":"Y when baseline exists and at least one non-baseline ACTOT value exists.","ANLTRT":"Planned randomized assignment from ADSL.TRT01P; actual treatment remains context.",
    "TRTDIFFL":"Y when planned TRT01P differs from actual TRT01A, else N.","STARTDT":"Origin date from ADSL.TRTSDT under the controlled TTDISC specification.","AVAL@ADTTE_RETENTION_STYLE":"ADT - STARTDT + 1 days.",
    "CNSR":"0 when DCSFL=Y; 1 when COMPLFL=Y under the exact event/censor partition.","EVNTDESC":"Discontinuation reason for events; controlled STUDY COMPLETED text for censors.",
}


def _sha256(path: Path) -> str:
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()


def _role(v: str) -> str:
    if v in {"STUDYID","USUBJID","AESEQ","QSSEQ"}: return "Identifier"
    if v.startswith("TRT") or v == "ANLTRT": return "Treatment"
    if v in TRACE: return "Traceability"
    if v in {"PARAM","PARAMCD","AVAL","BASE","CHG"}: return "Analysis"
    if v in DATES or v in {"ADY","ASTDY","AVISIT","AVISITN"}: return "Timing"
    return "Record Qualifier"


def build_metadata_catalog(config: dict[str, Any]) -> dict[str, Any]:
    if config.get("version") != VERSION: raise ValueError("metadata config version must be 0.18.0")
    ref=config.get("define_xml_reference",{})
    if ref.get("package_version") != "2.1.11" or ref.get("conformance") != "NOT_ASSESSED":
        raise ValueError("Define-XML reference must be 2.1.11 with conformance=NOT_ASSESSED")
    datasets=[]
    for name,ds in DATASETS.items():
        variables=[]
        for v in ds["columns"]:
            refs=SOURCES[name][v]
            origin="Predecessor" if v in PREDECESSOR[name] else "Derived"
            key=f"{v}@{name}"
            deriv=DERIVATION.get(key,DERIVATION.get(v, f"Derived deterministically from {', '.join(refs)} according to the portfolio analysis program." if origin=="Derived" else f"Copied or mapped from {', '.join(refs)} without changing analytical meaning."))
            variables.append({"name":v,"label":LABELS.get(v,v.replace("_"," ").title()),"data_type":"date" if v in DATES else "numeric" if v in NUMERIC else "text","role":_role(v),"origin_type":origin,"source_refs":refs,"derivation":deriv,"key":v in ds["keys"]})
        datasets.append({k:ds[k] for k in ["alias","file","label","class","keys"]}|{"name":name,"variables":variables})
    return {"version":VERSION,"metadata_model":"ADaM-style variable metadata and lineage portfolio evidence","define_xml_reference":ref,"datasets":datasets}


def validate_metadata_lineage(root: Path, catalog: dict[str, Any]) -> tuple[pd.DataFrame,dict[str,Any]]:
    root=Path(root); aliases={d["alias"]:{v["name"] for v in d["variables"]} for d in catalog["datasets"]}
    rows=[]; refs_total=analysis_refs=resolved=actual_total=0
    for ds in catalog["datasets"]:
        path=root/ds["file"]
        if not path.is_file(): raise ValueError(f"Metadata dataset file does not exist: {ds['file']}")
        actual=list(map(str,pd.read_csv(path,nrows=5).columns)); meta=[v["name"] for v in ds["variables"]]
        missing=sorted(set(actual)-set(meta)); extra=sorted(set(meta)-set(actual))
        if missing or extra or len(actual)!=len(meta): raise ValueError(f"{ds['name']} metadata coverage mismatch; missing={missing}; extra={extra}")
        if {v["name"] for v in ds["variables"] if v["key"]} != set(ds["keys"]): raise ValueError(f"{ds['name']} key metadata mismatch")
        actual_total += len(actual)
        for v in ds["variables"]:
            if v["origin_type"]=="Derived" and not v["derivation"].strip(): raise ValueError(f"{ds['name']}.{v['name']} requires derivation text")
            if not v["source_refs"] or not v["label"].strip(): raise ValueError(f"{ds['name']}.{v['name']} requires label and source refs")
            bad=[]
            for ref in v["source_refs"]:
                refs_total += 1
                if not REF_RE.fullmatch(ref): bad.append(ref); continue
                dom,var=ref.split(".",1)
                if dom in aliases:
                    analysis_refs += 1
                    if var in aliases[dom]: resolved += 1
                    else: bad.append(ref)
                elif dom not in RAW_DOMAINS: bad.append(ref)
            if bad: raise ValueError(f"{ds['name']}.{v['name']} unresolved source refs={bad}")
            rows.append({"dataset":ds["name"],"variable":v["name"],"label":v["label"],"data_type":v["data_type"],"role":v["role"],"origin_type":v["origin_type"],"source_refs":"|".join(v["source_refs"]),"derivation":v["derivation"],"key":v["key"],"dataset_sha256":_sha256(path),"passed":True})
    detail=pd.DataFrame(rows)
    metrics={"analysis_version":VERSION,"datasets":len(catalog["datasets"]),"actual_variables":actual_total,"metadata_variables":len(detail),"variables_with_exact_coverage":len(detail),"variable_coverage_pct":round(100*len(detail)/actual_total,4),"source_references":refs_total,"analysis_dataset_references":analysis_refs,"analysis_dataset_references_resolved":resolved,"derived_variables":int((detail.origin_type=="Derived").sum()),"predecessor_variables":int((detail.origin_type=="Predecessor").sum()),"define_xml_reference":"2.1.11","define_xml_conformance":"NOT_ASSESSED","all_passed":bool(len(detail)==actual_total and analysis_refs==resolved)}
    return detail,metrics


def build_define_like_xml(catalog: dict[str,Any]) -> ET.ElementTree:
    root=ET.Element("PortfolioDefineXMLLike",{"portfolioVersion":VERSION,"referenceStandard":"Define-XML","referencePackageVersion":"2.1.11","conformance":"NOT_ASSESSED"})
    ET.SubElement(root,"EvidenceBoundary").text="Define-XML-inspired portfolio export; schema conformance and submission readiness are not assessed."
    for ds in catalog["datasets"]:
        d=ET.SubElement(root,"DatasetDef",{"Name":ds["name"],"Label":ds["label"],"Class":ds["class"],"File":ds["file"],"Keys":" ".join(ds["keys"])})
        for i,v in enumerate(ds["variables"],1):
            item=ET.SubElement(d,"ItemDef",{"Name":v["name"],"Label":v["label"],"DataType":v["data_type"],"Role":v["role"],"OriginType":v["origin_type"],"OrderNumber":str(i),"Key":"Yes" if v["key"] else "No"})
            src=ET.SubElement(item,"SourceRefs")
            for ref in v["source_refs"]: ET.SubElement(src,"SourceRef",{"Ref":ref})
            ET.SubElement(item,"Derivation").text=v["derivation"]
    return ET.ElementTree(root)


def write_metadata_outputs(root: Path) -> dict[str,Any]:
    root=Path(root); config=json.loads((root/"spec"/"adam_metadata_config.json").read_text(encoding="utf-8")); catalog=build_metadata_catalog(config)
    detail,metrics=validate_metadata_lineage(root,catalog); out=root/"outputs"; out.mkdir(exist_ok=True)
    (out/"adam_variable_metadata.json").write_text(json.dumps(catalog,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    detail.to_csv(out/"metadata_lineage_validation.csv",index=False)
    tree=build_define_like_xml(catalog); ET.indent(tree,space="  "); xml=out/"define_xml_like_metadata.xml"; tree.write(xml,encoding="utf-8",xml_declaration=True)
    parsed=ET.parse(xml).getroot(); metrics.update({"xml_parse_passed":True,"xml_dataset_defs":len(parsed.findall("DatasetDef")),"xml_variable_defs":len(parsed.findall("./DatasetDef/ItemDef")),"define_like_xml_sha256":_sha256(xml)})
    metrics["xml_counts_match_metadata"]=metrics["xml_dataset_defs"]==metrics["datasets"] and metrics["xml_variable_defs"]==metrics["metadata_variables"]; metrics["all_passed"]=bool(metrics["all_passed"] and metrics["xml_counts_match_metadata"])
    (out/"metadata_lineage_metrics.json").write_text(json.dumps(metrics,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    summary=["# ADaM-style variable metadata and lineage validation","",f"- Portfolio metadata version: {VERSION}.",f"- Dataset definitions: {metrics['datasets']}.",f"- Exact variable coverage: {metrics['variables_with_exact_coverage']}/{metrics['actual_variables']} ({metrics['variable_coverage_pct']:.1f}%).",f"- Source references: {metrics['source_references']}.",f"- Analysis-dataset lineage references resolved: {metrics['analysis_dataset_references_resolved']}/{metrics['analysis_dataset_references']}.",f"- XML dataset / variable definitions: {metrics['xml_dataset_defs']} / {metrics['xml_variable_defs']}.","- Define-XML reference package: 2.1.11; conformance status: NOT_ASSESSED.","","The XML is a deterministic Define-XML-inspired portfolio export. It is not claimed to be ODM/Define-XML schema-conformant, submission-ready metadata, or regulatory validation evidence."]
    (out/"metadata_lineage_summary.md").write_text("\n".join(summary)+"\n",encoding="utf-8")
    if not metrics["all_passed"]: raise ValueError("Metadata lineage validation failed")
    return metrics
