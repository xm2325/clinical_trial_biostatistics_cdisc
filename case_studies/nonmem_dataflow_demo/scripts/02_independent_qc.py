#!/usr/bin/env python3
"""Independent source-to-output verification, not clinical/GxP validation."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime
from pathlib import Path
import hashlib
import math

DATA = Path("case_studies/nonmem_dataflow_demo/data")
OUT = Path("outputs/nonmem_demo")
COLS = ("ID","TIME","TAD","EVID","MDV","DV","AMT","RATE","CMT","WT","AGE","SEX","BLQ","LLOQ")

def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))

def stamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")

def qc(source: Path, output: Path) -> list[dict[str, str]]:
    # Intentionally reconstruct from source instead of using the R builder's calculations.
    dm, ex, pc, vs = (read_csv(source / f"{x}.csv") for x in ("dm","ex","pc","vs"))
    review = read_csv(output / "data/nonmem_input_review.csv")
    crosswalk = read_csv(output / "metadata/subject_crosswalk.csv")
    issues = []
    def check(subject: str, name: str, good: bool, finding: str, action: str):
        issues.append(dict(subject=subject, check=name, result="PASS" if good else "FAIL",
                           finding="" if good else finding, follow_up="" if good else action,
                           qc_script="02_independent_qc.py"))
    check("ALL","column_order", bool(review) and tuple(review[0]) == COLS,
          "Unexpected columns or empty export","Resolve dataset specification mismatch")
    idmap = {r["USUBJID"]: int(r["ID"]) for r in crosswalk}
    check("ALL","subject_mapping", set(idmap) == {r["USUBJID"] for r in dm}
          and len(idmap) == len(dm) and len(set(idmap.values())) == len(idmap),
          "Crosswalk missing or duplicate subjects","Rebuild subject crosswalk")
    if not review or tuple(review[0]) != COLS or set(idmap) != {r["USUBJID"] for r in dm}:
        return issues
    for person in dm:
        s = person["USUBJID"]
        dose = sorted((r for r in ex if r["USUBJID"] == s), key=lambda r: r["EXSTDTC"])
        conc = sorted((r for r in pc if r["USUBJID"] == s), key=lambda r: r["PCDTC"])
        weight = [r for r in vs if r["USUBJID"] == s and r["VSTESTCD"] == "WEIGHT"]
        subject_rows = [r for r in review if int(r["ID"]) == idmap[s]]
        if not dose or len(weight) != 1:
            check(s,"source_coverage",False,"Missing dose or nonunique baseline weight","Resolve source records")
            continue
        first = stamp(dose[0]["EXSTDTC"])
        wt = float(weight[0]["VSSTRESN"]) * (0.001 if weight[0]["VSSTRESU"] == "g" else 1)
        sex = int(person["SEX"] == "M")
        expected = []
        for r in dose:
            h = (stamp(r["EXSTDTC"]) - first).total_seconds() / 3600
            amt = float(r["EXDOSE"]) * (0.001 if r["EXDOSU"] == "ug" else 1)
            expected.append([idmap[s], h,0,1,1,0,amt,0,1,wt,float(person["AGE"]),sex,0,0])
        for r in conc:
            t = stamp(r["PCDTC"])
            prior = [stamp(e["EXSTDTC"]) for e in dose if stamp(e["EXSTDTC"]) <= t]
            if not prior:
                check(s,"sample_time",False,"PK sample precedes first dose","Query timing / data collection")
                continue
            blq = int(r["BLQ_FLAG"] == "Y")
            expected.append([idmap[s],(t-first).total_seconds()/3600,
                (t-max(prior)).total_seconds()/3600,0,blq,
                0 if blq else float(r["PCSTRESN"]),0,0,2,wt,
                float(person["AGE"]),sex,blq,float(r["LLOQ_NG_ML"])])
        expected.sort(key=lambda row: (row[0],row[1],-row[3]))
        check(s,"record_count",len(expected) == len(subject_rows),
              "Dose/observation count mismatch","Investigate EX/PC event coverage")
        if len(expected) != len(subject_rows):
            continue
        for idx,(exp,act) in enumerate(zip(expected,subject_rows),1):
            valid = all(math.isclose(float(act[k]),float(ref),rel_tol=1e-9,abs_tol=1e-9)
                        for k,ref in zip(COLS,exp))
            check(s,f"record_{idx:03d}",valid,
                  f"Source-derived values differ at record {idx}",
                  "Review timestamps, dose units, MDV/BLQ, LLOQ and covariates")
    expected_count = len(ex)+len(pc)
    check("ALL","total_records", len(review) == expected_count,
          f"Expected {expected_count} events; found {len(review)}","Reconcile source events")
    lines = (output/"data/nonmem_input.csv").read_text(encoding="utf-8").splitlines()
    check("ALL","headerless_export",len(lines) == len(review) and
          all(len(line.split(",")) == len(COLS) for line in lines),
          "NONMEM text row count or field count differs","Re-export headerless NONMEM dataset")
    manifest = read_csv(output/"metadata/manifest.csv")
    hashes_valid = bool(manifest) and all(
        (lambda p: p.is_file() and hashlib.md5(p.read_bytes()).hexdigest() == r["md5"])
        (Path(r["path"])) for r in manifest)
    check("ALL","manifest_hashes",hashes_valid,
          "Output file was modified after manifest creation","Regenerate manifest and re-run QC")
    return issues

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-dir",type=Path,default=DATA)
    parser.add_argument("--output-dir",type=Path,default=OUT)
    args=parser.parse_args()
    log_dir=args.output_dir/"qc"
    log_dir.mkdir(parents=True,exist_ok=True)
    try:
        checks=qc(args.source_dir,args.output_dir)
    except (OSError,ValueError,KeyError,TypeError) as err:
        checks=[dict(subject="ALL",check="qc_runtime",result="FAIL",
                     finding=f"{type(err).__name__}: {err}",
                     follow_up="Check inputs and rerun",qc_script="02_independent_qc.py")]
    with (log_dir/"qc_log.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=["subject","check","result","finding","follow_up","qc_script"])
        writer.writeheader();writer.writerows(checks)
    bad=[c for c in checks if c["result"] != "PASS"]
    (log_dir/"qc_summary.md").write_text(
        f"# Synthetic NONMEM dataflow independent QC\n\n"
        f"Checks: {len(checks)}; PASS: {len(checks)-len(bad)}; FAIL: {len(bad)}.\n\n"
        "This checks a small synthetic example and is not formal clinical validation.\n",
        encoding="utf-8")
    print(f"NONMEM independent QC: {len(checks)-len(bad)}/{len(checks)} PASS")
    return 1 if bad else 0

if __name__=="__main__":
    raise SystemExit(main())
