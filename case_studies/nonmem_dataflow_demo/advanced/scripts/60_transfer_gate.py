#!/usr/bin/env python3
"""Audited pre-build intake gate for the SYNTHETIC PK transfer exercise.

This is a training quality gate, not sponsor SOP execution, SDTM CORE conformance,
GxP-qualified validation or an electronic clinical data transfer.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path("case_studies/nonmem_dataflow_demo/advanced/data")
DEFAULT_OUT = Path("outputs/nonmem_advanced/m3")
FIELDS = {
    "dm": ("USUBJID", "AGE", "SEX"),
    "ex": ("USUBJID", "EXSEQ", "EXSTDTC", "EXDOSE", "EXDOSU", "EXROUTE", "EXDURH"),
    "pc": ("USUBJID", "PCSEQ", "PCDTC", "PCSTRESN", "PCSTRESU", "BLQ_FLAG", "LLOQ_NG_ML"),
    "vs": ("USUBJID", "VSDTC", "VSTESTCD", "VSSTRESN", "VSSTRESU"),
}
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")


def read_table(path: Path) -> tuple[list[dict[str, str]], tuple[str, ...]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("empty or malformed CSV header")
        return list(reader), tuple(reader.fieldnames)


def moment(raw: str | None) -> datetime | None:
    if raw is None or not ISO.fullmatch(raw):
        return None
    try:
        dt = datetime.strptime(raw, "%Y-%m-%dT%H:%M:%S")
        if dt.strftime("%Y-%m-%dT%H:%M:%S") != raw:
            return None
        return dt
    except ValueError:
        return None


def positive(raw: str | None, allow_zero: bool = False) -> float | None:
    try:
        num = float(raw) if raw is not None else float("nan")
        if math.isfinite(num) and (num >= 0 if allow_zero else num > 0):
            return num
    except (ValueError, TypeError):
        pass
    return None


def audit(source: Path) -> tuple[list[dict[str, str]], dict]:
    queries: list[dict[str, str]] = []
    data: dict[str, list[dict[str, str]]] = {}
    digest: dict[str, str] = {}

    def query(code, table, key, field, detail, action, severity="ERROR"):
        queries.append(dict(query_id=f"Q{len(queries)+1:04d}",
            code=code, table=table.upper(), source_key=key,
            field=field, severity=severity, status="OPEN",
            finding=detail, proposed_action=action,
            reviewer="", decision="", resolution_evidence=""))

    for table, expected in FIELDS.items():
        p = source / f"{table}.csv"
        if not p.is_file():
            query("MISSING_FILE", table, "FILE", "", f"{p} does not exist",
                  "Obtain source file and record its provenance.")
            data[table] = []
            continue
        digest[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
        try:
            records, cols = read_table(p)
            missing = set(expected) - set(cols)
            if missing:
                query("SCHEMA_MISSING", table, "FILE", "",
                    f"Missing required columns: {sorted(missing)}",
                    "Resolve transfer mapping and resend the file.")
            data[table] = records if not missing else []
            if not records:
                query("EMPTY_DOMAIN", table, "FILE", "",
                      "No source records", "Resolve source extract.")
            for i, record in enumerate(records, 1):
                if None in record:
                    query("CSV_EXTRA_FIELDS", table, f"ROW:{i}", "",
                          "More fields than header", "Correct malformed CSV transfer.")
                if any(value is None for value in record.values()):
                    query("CSV_SHORT_ROW", table, f"ROW:{i}", "",
                          "Fewer fields than header", "Correct malformed CSV transfer.")
        except (OSError, UnicodeError, ValueError, csv.Error) as exc:
            data[table] = []
            query("READ_FAILED", table, "FILE", "", str(exc),
                  "Resolve encoding and transfer file integrity.")

    def record_key(table, row, ordinal):
        if table in {"ex", "pc"}:
            return str(row.get("USUBJID") or "?") + ":" + str(row.get(table.upper()+"SEQ") or ordinal)
        return str(row.get("USUBJID") or ordinal)

    for table, records in data.items():
        seen = set()
        for n, r in enumerate(records, 1):
            k = record_key(table, r, n)
            sub = r.get("USUBJID")
            if not sub:
                query("MISSING_SUBJECT", table, k, "USUBJID",
                      "USUBJID missing", "Raise data collection query.")
            if table in {"dm","ex","pc"}:
                key = (sub,) if table=="dm" else (sub,r.get(table.upper()+"SEQ"))
                if not all(key):
                    query("MISSING_SOURCE_SEQ", table, k, table.upper()+"SEQ",
                          "Sequence identifier missing", "Query source identifier.")
                if key in seen:
                    query("DUPLICATE_SOURCE_KEY", table, k, "",
                          "Duplicate subject/sequence key", "Investigate repeated or merged transfer.")
                seen.add(key)

    dm_subjects={r.get("USUBJID") for r in data["dm"] if r.get("USUBJID")}
    ex_subjects={r.get("USUBJID") for r in data["ex"] if r.get("USUBJID")}
    pc_subjects={r.get("USUBJID") for r in data["pc"] if r.get("USUBJID")}
    vs_subjects={r.get("USUBJID") for r in data["vs"] if r.get("USUBJID")}
    for table, sub_set in (("ex",ex_subjects),("pc",pc_subjects),("vs",vs_subjects)):
        if sub_set != dm_subjects:
            query("SUBJECT_COVERAGE",table,"ALL","USUBJID",
                  f"Expected DM subjects {sorted(dm_subjects)}, observed {sorted(sub_set)}",
                  "Reconcile transfer coverage and subject roster.")

    for r in data["dm"]:
        s = r.get("USUBJID") or "?"
        if positive(r.get("AGE")) is None:
            query("AGE_INVALID","dm",s,"AGE","Invalid age","Query demographic record.")
        if r.get("SEX") not in ("M","F"):
            query("SEX_INVALID","dm",s,"SEX","Unexpected sex encoding","Confirm controlled terminology.")

    ex_by_subject = {}
    pc_by_subject = {}
    vs_by_subject = {}
    for i,r in enumerate(data["ex"],1):
        k=record_key("ex",r,i)
        s=r.get("USUBJID") or "?"
        date=moment(r.get("EXSTDTC"))
        if date is None:
            query("EX_TIME_INVALID","ex",k,"EXSTDTC",
                  "Missing, partial or impossible EX timestamp",
                  "Query actual dose start; do not impute.")
        amount=positive(r.get("EXDOSE"))
        if amount is None:
            query("DOSE_INVALID","ex",k,"EXDOSE","Dose must be a finite positive number",
                  "Resolve dose record.")
        if r.get("EXDOSU") not in ("mg","ug"):
            query("DOSE_UNIT_INVALID","ex",k,"EXDOSU",
                  "Unsupported dose unit","Confirm unit conversion specification.")
        route=r.get("EXROUTE")
        dur=positive(r.get("EXDURH"),allow_zero=True)
        if route not in ("ORAL","IV_INFUSION"):
            query("ROUTE_INVALID","ex",k,"EXROUTE",
                  "Unsupported route","Confirm route and model compartment.")
        if dur is None or (route=="ORAL" and dur!=0) or (route=="IV_INFUSION" and dur==0):
            query("DURATION_INVALID","ex",k,"EXDURH",
                  "Oral duration must be zero; IV infusion duration strictly positive",
                  "Resolve actual infusion duration and derived RATE.")
        if date is not None:
            ex_by_subject.setdefault(s,[]).append((date,k,dur if dur else 0,route))
    for s,events in ex_by_subject.items():
        events.sort()
        for old,new in zip(events,events[1:]):
            if old[0]==new[0]:
                query("SAME_TIME_DOSE","ex",new[1],"EXSTDTC",
                    "Two dose starts at exactly the same time",
                    "Confirm separate administrations rather than transfer duplication.",
                    severity="WARNING")
            if old[3]=="IV_INFUSION" and old[2]>0 and new[0]<old[0] + __import__("datetime").timedelta(hours=old[2]):
                query("OVERLAPPING_INFUSIONS","ex",new[1],"EXSTDTC",
                    "New dose starts before previous infusion finishes",
                    "Confirm overlapping infusions were intended.", severity="WARNING")

    for i,r in enumerate(data["pc"],1):
        k=record_key("pc",r,i)
        s=r.get("USUBJID") or "?"
        date=moment(r.get("PCDTC"))
        if date is None:
            query("PC_TIME_INVALID","pc",k,"PCDTC",
                  "Missing, partial or impossible sample collection timestamp",
                  "Query actual sample time; do not infer from nominal visit.")
        unit=r.get("PCSTRESU")
        if unit not in ("ng/mL","ug/L","mg/L"):
            query("CONC_UNIT_INVALID","pc",k,"PCSTRESU",
                  "Unexpected PK concentration unit","Resolve units before conversion.")
        ll=positive(r.get("LLOQ_NG_ML"))
        if ll is None:
            query("LLOQ_INVALID","pc",k,"LLOQ_NG_ML",
                  "LLOQ must be a positive number","Resolve assay lower limit.")
        flag=r.get("BLQ_FLAG")
        if flag not in ("Y","N"):
            query("BLQ_FLAG_INVALID","pc",k,"BLQ_FLAG",
                  "BLQ flag not Y or N","Clarify censoring status.")
        value=r.get("PCSTRESN")
        if flag=="Y":
            if value not in (None,""):
                query("BLQ_VALUE_CONFLICT","pc",k,"PCSTRESN",
                      "BLQ marked, yet numeric measured value supplied",
                      "Confirm data conventions; do not invent a measured concentration.")
        elif flag=="N":
            v=positive(value,allow_zero=True)
            if v is None:
                query("CONC_INVALID","pc",k,"PCSTRESN",
                      "Non-BLQ sample has missing, negative or non-finite value",
                      "Query assay result.")
            elif unit in ("ng/mL","ug/L","mg/L") and ll is not None:
                ng_ml=v*(1000 if unit=="mg/L" else 1)
                if ng_ml<ll:
                    query("BELOW_LLOQ_UNFLAGGED","pc",k,"PCSTRESN",
                          f"Observed {ng_ml:.8g} ng/mL lower than LLOQ {ll:.8g} ng/mL",
                          "Resolve BLQ flag/value convention with data owner.")
        if date is not None:
            pc_by_subject.setdefault(s,[]).append((date,k))
    for s,entries in pc_by_subject.items():
        for date,key in entries:
            first=min((x[0] for x in ex_by_subject.get(s,[])),default=None)
            if first is not None and date<first:
                query("PREDOSE_SAMPLE","pc",key,"PCDTC",
                      "Sample collected before first recorded dose",
                      "Confirm baseline sample is intended or reconcile dosing history.")
            if any(x[0]==date for x in ex_by_subject.get(s,[])):
                query("SAME_TIME_SAMPLE_DOSE","pc",key,"PCDTC",
                      "Sample timestamp equals a dose start",
                      "Review intended pre-dose/post-dose ordering.",severity="WARNING")

    for i,r in enumerate(data["vs"],1):
        k=record_key("vs",r,i)
        s=r.get("USUBJID") or "?"
        vs_by_subject.setdefault(s,[]).append(r)
        if r.get("VSTESTCD")!="WEIGHT":
            query("VS_TEST_UNSUPPORTED","vs",k,"VSTESTCD",
                  "Non-weight vital sign in training source","Confirm input mapping.")
        if r.get("VSSTRESU") not in ("kg","g"):
            query("WEIGHT_UNIT_INVALID","vs",k,"VSSTRESU",
                  "Unsupported weight unit","Clarify unit and conversion.")
        if positive(r.get("VSSTRESN")) is None:
            query("WEIGHT_INVALID","vs",k,"VSSTRESN",
                  "Missing or implausibly nonpositive weight","Query measurement.")
        date=moment(r.get("VSDTC"))
        if date is None:
            query("VS_TIME_INVALID","vs",k,"VSDTC",
                  "Missing, partial or impossible weight timestamp",
                  "Confirm baseline measurement time.")
        else:
            first=min((x[0] for x in ex_by_subject.get(s,[])),default=None)
            if first is not None and date>first:
                query("POSTDOSE_WEIGHT","vs",k,"VSDTC",
                    "Demo requires weight strictly at or before first dose",
                    "Choose documented baseline covariate.")
    for subject in dm_subjects:
        if len(vs_by_subject.get(subject,[]))!=1:
            query("VS_CARDINALITY","vs",subject,"USUBJID",
                "Expected exactly one baseline weight per subject",
                "Confirm baseline covariate selection.")

    errors=sum(x["severity"]=="ERROR" for x in queries)
    warnings=len(queries)-errors
    state="PASS" if errors==0 else "HOLD"
    summary=dict(state=state,source_dir=str(source),source_sha256=digest,
                 records={k:len(v) for k,v in data.items()},
                 blocking_queries=errors,warning_queries=warnings,
                 open_queries=len(queries),
                 training_boundary="SYNTHETIC; no sponsor/CRO data or qualification",
                 query_rule_set="PK_TRANSFER_TRAINING_V1")
    return queries,summary


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--source-dir",type=Path,default=ROOT)
    p.add_argument("--output-dir",type=Path,default=DEFAULT_OUT)
    p.add_argument("--strict-warnings",action="store_true")
    args=p.parse_args()
    entries,summary=audit(args.source_dir)
    dest=args.output_dir/"intake"
    dest.mkdir(parents=True,exist_ok=True)
    fields=("query_id","code","table","source_key","field","severity","status",
            "finding","proposed_action","reviewer","decision","resolution_evidence")
    with (dest/"transfer_query_log.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(entries)
    (dest/"transfer_report.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(f"PK synthetic transfer: {summary['state']} | "
          f"{summary['blocking_queries']} blocking | {summary['warning_queries']} warnings")
    for r in entries:
        print(f"  {r['severity']} {r['code']}: {r['source_key']} {r['finding']}")
    return int(summary["state"]!="PASS" or
               (args.strict_warnings and summary["warning_queries"]>0))


if __name__=="__main__":
    raise SystemExit(main())
