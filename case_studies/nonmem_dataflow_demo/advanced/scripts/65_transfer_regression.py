#!/usr/bin/env python3
"""Negative-case regression suite for synthetic PK transfer query gate."""
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

SOURCE=Path("case_studies/nonmem_dataflow_demo/advanced/data")
GATE="case_studies/nonmem_dataflow_demo/advanced/scripts/60_transfer_gate.py"

def run(source,output):
    proc=subprocess.run([sys.executable,GATE,"--source-dir",str(source),
                         "--output-dir",str(output)],capture_output=True,text=True)
    with (output/"intake/transfer_query_log.csv").open(newline="",encoding="utf-8") as stream:
        rows=list(csv.DictReader(stream))
    report=json.loads((output/"intake/transfer_report.json").read_text(encoding="utf-8"))
    return proc,rows,report

def alter(path,func):
    with path.open(newline="",encoding="utf-8") as f: rows=list(csv.DictReader(f))
    columns=list(rows[0])
    func(rows)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(rows)

def main():
    with tempfile.TemporaryDirectory(prefix="pk-transfer-case-") as dirname:
        root=Path(dirname)
        proc,entries,report=run(SOURCE,root/"control")
        assert proc.returncode==0 and report["state"]=="PASS",proc.stdout+proc.stderr
        assert "SAME_TIME_SAMPLE_DOSE" in {x["code"] for x in entries}
        cases=[
          ("duplicate_PCSEQ","pc.csv",lambda r:r[1].__setitem__("PCSEQ",r[0]["PCSEQ"]),"DUPLICATE_SOURCE_KEY"),
          ("partial_datetime","pc.csv",lambda r:r[0].__setitem__("PCDTC","2026-01-01"),"PC_TIME_INVALID"),
          ("impossible_date","pc.csv",lambda r:r[0].__setitem__("PCDTC","2026-02-30T12:00:00"),"PC_TIME_INVALID"),
          ("unflagged_BLQ","pc.csv",lambda r:r[0].__setitem__("PCSTRESN","1"),"BELOW_LLOQ_UNFLAGGED"),
          ("negative_dose","ex.csv",lambda r:r[0].__setitem__("EXDOSE","-1"),"DOSE_INVALID"),
          ("infusion_zero_duration","ex.csv",lambda r:r[2].__setitem__("EXDURH","0"),"DURATION_INVALID"),
          ("missing_dose_timestamp","ex.csv",lambda r:r[0].__setitem__("EXSTDTC",""),"EX_TIME_INVALID"),
          ("unknown_concentration_unit","pc.csv",lambda r:r[0].__setitem__("PCSTRESU","mg/mL"),"CONC_UNIT_INVALID"),
          ("postdose_weight","vs.csv",lambda r:r[0].__setitem__("VSDTC","2026-01-03T12:00:00"),"POSTDOSE_WEIGHT"),
          ("BLQ_with_observed_value","pc.csv",
            lambda r:next(x for x in r if x["BLQ_FLAG"]=="Y").__setitem__("PCSTRESN","0.05"),
            "BLQ_VALUE_CONFLICT"),
        ]
        for name,filename,edit,code in cases:
            src=root/name/"source"
            shutil.copytree(SOURCE,src)
            alter(src/filename,edit)
            result,queries,report=run(src,root/name/"output")
            errors={r["code"] for r in queries if r["severity"]=="ERROR"}
            assert result.returncode!=0 and report["state"]=="HOLD" and code in errors, (name,errors,result.stdout)
            print(f"PASS: {name} -> blocked {code}")
        print(f"PK transfer intake: 1 clean fixture + {len(cases)} negative cases PASS")
        return 0

if __name__=="__main__":raise SystemExit(main())
