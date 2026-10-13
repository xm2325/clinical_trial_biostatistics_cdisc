#!/usr/bin/env python3
"""Optional NONMEM nmfe7x invocation if the USER supplies a licensed executable.

Default is plan-only and NEVER runs NONMEM. This wrapper is not exercised with
NONMEM by CI; a Python plan smoke test is NOT evidence of NONMEM estimation.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess

COLUMNS = ("ID","TIME","TAD","EVID","MDV","DV","AMT","RATE","CMT",
           "WT","AGE","SEX","BLQ","LLOQ","CENS")


def prepare(output:Path)->tuple[Path,Path]:
    mode=(output/"metadata/blq_mode.txt").read_text(encoding="utf-8").strip()
    if mode not in {"m1","m3"}:raise ValueError("Unsupported BLQ strategy")
    control=output/"model"/f"one_compartment_{mode}_unexecuted.ctl"
    data=output/"data/nonmem_input.csv"
    review=output/"data/nonmem_input_review.csv"
    for f in (control,data,review):
        if not f.is_file() or f.stat().st_size==0:raise ValueError(f"Input absent: {f}")
    with review.open(newline="",encoding="utf-8") as stream:
        reader=csv.DictReader(stream)
        if tuple(reader.fieldnames or ())!=COLUMNS+("SOURCE_KEY",):
            raise ValueError("NONMEM input schema mismatch")
        nrows=sum(1 for _ in reader)
    if nrows!=len(data.read_text(encoding="utf-8").splitlines()):
        raise ValueError("NONMEM data row count mismatch")
    ctl_text=control.read_text(encoding="utf-8")
    if "$INPUT "+" ".join(COLUMNS) not in ctl_text:
        raise ValueError("Control-file $INPUT order mismatches dataset")
    if "$DATA ../data/nonmem_input.csv" not in ctl_text:
        raise ValueError("Control-file relative $DATA link mismatches workspace")
    working=output/"licensed_run"
    if working.exists(): shutil.rmtree(working)
    for section in ("data","model"):
        (working/section).mkdir(parents=True)
    shutil.copy2(control,working/"model"/control.name)
    shutil.copy2(data,working/"data"/data.name)
    return working,working/"model"/control.name


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",type=Path,default=Path("outputs/nonmem_advanced/m3"))
    ap.add_argument("--executable",help="Path to USER-LICENSED nmfe75/nmfe76 wrapper (no bundled executable)")
    ap.add_argument("--execute",action="store_true",help="Explicitly attempt licensed NONMEM execution")
    ap.add_argument("--timeout-seconds",type=int,default=900)
    args=ap.parse_args()
    if args.timeout_seconds<1:raise SystemExit("Timeout must be positive")
    try:
        working,control=prepare(args.output_dir)
        status={
          "mode":"EXECUTE" if args.execute else "PLAN_ONLY",
          "NONMEM_executed":False,
          "NONMEM_validated":False,
          "model_qualified":False,
          "input":str(control),
          "report":"model/run.res",
          "claim":"NONE; plan is not execution and zero exit is not model validation",
        }
        output=working/"execution_status.json"
        if not args.execute:
            status["required_command"]="nmfe75 "+control.name+" run.res"
            status["note"]="Supply --execute --executable /path/to/licensed/nmfe75 when a valid installation is available. Control stream is untested."
            output.write_text(json.dumps(status,indent=2)+"\n",encoding="utf-8")
            print("NONMEM plan generated only; NO NONMEM EXECUTION")
            return 0
        if not args.executable:
            raise ValueError("--execute requires --executable /path/to/licensed/nmfeXX")
        executable=shutil.which(args.executable)
        if not executable or not Path(executable).is_file():
            raise ValueError("Licensed NONMEM executable not found")
        proc=subprocess.run([executable,control.name,"run.res"],cwd=control.parent,
             capture_output=True,text=True,timeout=args.timeout_seconds,check=False)
        (working/"console_stdout.txt").write_text(proc.stdout,encoding="utf-8")
        (working/"console_stderr.txt").write_text(proc.stderr,encoding="utf-8")
        report=working/"model"/"run.res"
        status["NONMEM_executed"]=True
        status["return_code"]=proc.returncode
        status["report_exists"]=report.is_file() and report.stat().st_size>0
        status["result_status"]="PROCESS_RETURNED_ZERO_REQUIRES_SCIENTIFIC_REVIEW" \
             if proc.returncode==0 and status["report_exists"] else "FAILED"
        output.write_text(json.dumps(status,indent=2)+"\n",encoding="utf-8")
        print("NONMEM invocation:",status["result_status"])
        return 0 if proc.returncode==0 and status["report_exists"] else 1
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        print(f"NONMEM execution/plan unavailable: {type(exc).__name__}: {exc}")
        return 2


if __name__=="__main__":
    raise SystemExit(main())
