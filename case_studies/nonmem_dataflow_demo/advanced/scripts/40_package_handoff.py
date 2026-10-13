#!/usr/bin/env python3
"""Build an auditable synthetic NONMEM submission-style example, not a regulatory submission."""
import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path

def read(path):
    with path.open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build(out):
    mode=(out/"metadata/blq_mode.txt").read_text(encoding="utf-8").strip()
    if mode not in ("m1","m3"):raise ValueError("invalid BLQ mode")
    checks=read(out/"qc/qc_log.csv")
    if not checks or any(r["result"]!="PASS" for r in checks):
        raise ValueError("failed/missing independent QC; refuse release")
    gate=out/"intake/transfer_report.json"
    intake=json.loads(gate.read_text(encoding="utf-8"))
    if intake.get("state")!="PASS" or intake.get("blocking_queries")!=0:
        raise ValueError("intake transfer HOLD or missing gate evidence; refuse release")
    raw_dir=Path("case_studies/nonmem_dataflow_demo/advanced/data")
    source_hashes=intake.get("source_sha256",{})
    for name in ("dm.csv","ex.csv","pc.csv","vs.csv"):
        if name not in source_hashes or sha256(raw_dir/name)!=source_hashes[name]:
            raise ValueError("intake source changed after audit: "+name)
    validation=(out/"validation/pk_crosscheck_summary.md").read_text(encoding="utf-8")
    if "PASS" not in validation or "No PK parameter fitting or NONMEM execution" not in validation:
        raise ValueError("structural PK validation report missing")
    dest=out/"handoff"
    if dest.exists():shutil.rmtree(dest)
    for d in ("data","model","metadata","qc","validation","documents","intake","source"):
        (dest/d).mkdir(parents=True,exist_ok=True)
    parts=[
      ("data/nonmem_input.csv","model data"),
      ("data/nonmem_input_review.csv","review data"),
      (f"model/one_compartment_{mode}_unexecuted.ctl","unexecuted example model"),
      ("metadata/subject_crosswalk.csv","subject crosswalk"),
      ("metadata/variable_definitions.csv","data dictionary"),
      ("metadata/blq_mode.txt","censoring specification"),
      ("qc/qc_log.csv","independent QC"),
      ("qc/qc_summary.md","QC summary"),
      ("validation/pk_crosscheck.csv","independent predictions"),
      ("validation/pk_crosscheck_summary.md","model validation report"),
      ("intake/transfer_report.json","source transfer audit and hashes"),
      ("intake/transfer_query_log.csv","source queries and reviewer actions")
    ]
    for relative,_ in parts:shutil.copyfile(out/relative,dest/relative)
    for filename in ("dm.csv","ex.csv","pc.csv","vs.csv"):
        relative="source/"+filename
        shutil.copyfile(raw_dir/filename,dest/relative)
        parts.append((relative,"synthetic source snapshot"))
    links=[
      {"source":f"model/one_compartment_{mode}_unexecuted.ctl",
       "relation":"$DATA","target":"data/nonmem_input.csv"},
      {"source":"metadata/variable_definitions.csv",
       "relation":"defines","target":"data/nonmem_input_review.csv"},
      {"source":"qc/qc_log.csv","relation":"QC of","target":"data/nonmem_input_review.csv"},
      {"source":"validation/pk_crosscheck.csv","relation":"fixed-parameter model of","target":"data/nonmem_input.csv"},
      {"source":"intake/transfer_query_log.csv","relation":"source intake questions for",
       "target":"source/pc.csv"}
    ]
    with (dest/"metadata/file_links.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=("source","relation","target"));w.writeheader();w.writerows(links)
    (dest/"documents/process_note.md").write_text(
        "# Synthetic NONMEM-style handoff\n\n"
        f"BLQ mode: {mode}. All subjects and concentrations are invented.\n\n"
        "R source mapping, Python source reconstruction QC and scipy ODE cross-check "
        "are runnable, whereas the NONMEM control file is unexecuted.\n\n"
        "The intake audit passes all blocking transfer rules and retains "
        "source tables and documented source hashes. Warnings remain open "
        "for human review and no silent corrections are applied.\n\n"
        "There is no actual parameter estimation, real run output, licensed NONMEM "
        "verification, official Define-XML file, EPOD assembly, sponsor-approved "
        "tsDTA, vendor exchange, GxP qualification or regulatory e-submission.\n",
        encoding="utf-8")
    (dest/"documents/evidence_boundary.json").write_text(json.dumps({
      "synthetic":True,"QC_passed":True,"intake_transfer_passed":True,
      "PK_ODE_crosscheck_passed":True,"NONMEM_model_executed":False,
      "real_e_submission":False,"formal_define_xml":False,
      "sponsor_approval":False,"mode":mode
    },indent=2)+"\n",encoding="utf-8")
    parts += [("metadata/file_links.csv","relative links"),
              ("documents/process_note.md","evidence limitations"),
              ("documents/evidence_boundary.json","permitted claim limits")]
    with (dest/"metadata/file_index.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=("path","role","sha256"));w.writeheader()
        w.writerows({"path":p,"role":role,"sha256":sha256(dest/p)} for p,role in parts)
    return dest

def verify(dest):
    issues=[]
    try:
        index=read(dest/"metadata/file_index.csv")
        referenced={r["path"] for r in index}
        if len(index)<10 or len(index)!=len(referenced):issues.append("bad manifest cardinality")
        for row in index:
            path=Path(row["path"])
            if path.is_absolute() or ".." in path.parts:issues.append("unsafe path");continue
            if not (dest/path).is_file():issues.append("missing "+str(path));continue
            if sha256(dest/path)!=row["sha256"]:issues.append("checksum mismatch "+str(path))
        for link in read(dest/"metadata/file_links.csv"):
            if link["source"] not in referenced or link["target"] not in referenced:
                issues.append("broken indexed reference "+link["source"])
        if "intake/transfer_report.json" not in referenced:
            issues.append("no intake gate evidence")
        else:
            gate=json.loads((dest/"intake/transfer_report.json").read_text(encoding="utf-8"))
            if gate.get("state")!="PASS" or gate.get("blocking_queries")!=0:
                issues.append("intake gate reports HOLD")
            for file,checksum in gate.get("source_sha256",{}).items():
                snap=dest/"source"/file
                if not snap.is_file() or sha256(snap)!=checksum:
                    issues.append("source hash mismatch "+file)
        models=list((dest/"model").glob("*.ctl"))
        if len(models)!=1 or "$DATA ../data/nonmem_input.csv" not in models[0].read_text():
            issues.append("bad model-data link")
        if not read(dest/"qc/qc_log.csv") or any(
          r["result"]!="PASS" for r in read(dest/"qc/qc_log.csv")):issues.append("QC not clean")
    except (OSError,ValueError,KeyError,csv.Error) as e:
        issues.append(f"{type(e).__name__}: {e}")
    return issues

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",type=Path,default=Path("outputs/nonmem_advanced/m3"))
    parser.add_argument("--verify-only",action="store_true")
    args=parser.parse_args()
    try:
        dest=args.output_dir/"handoff" if args.verify_only else build(args.output_dir)
        issues=verify(dest)
    except (OSError,ValueError,KeyError) as e:issues=[str(e)]
    for item in issues:print("FAIL:",item)
    if not issues:print("Synthetic handoff file-link and SHA256 verification PASS")
    return int(bool(issues))

if __name__=="__main__":raise SystemExit(main())
