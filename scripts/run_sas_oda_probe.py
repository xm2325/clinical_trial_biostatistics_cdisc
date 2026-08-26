from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pandas as pd
import saspy


ERROR_LINE = re.compile(r"^\s*ERROR(?:\s+\d+-\d+)?:", re.IGNORECASE)


def _sas_error_lines(log: str) -> list[str]:
    return [line.strip() for line in log.splitlines() if ERROR_LINE.match(line)]


def main() -> None:
    cfgfile = Path(os.environ.get("SASPY_CFGFILE", ""))
    if not cfgfile.is_file():
        raise RuntimeError("SASPY_CFGFILE does not point to the generated SASPy configuration")

    outputs = Path("outputs")
    outputs.mkdir(parents=True, exist_ok=True)

    sas = None
    try:
        sas = saspy.SASsession(cfgname="oda", cfgfile=str(cfgfile), results="TEXT")
        program = r'''
data work.oda_ci_probe;
  length execution_source $32;
  do probe_id = 1 to 3;
    probe_value = probe_id * 10;
    execution_source = "GITHUB_ACTIONS_SASPY";
    output;
  end;
run;

proc sql noprint;
  select count(*) into :oda_ci_probe_rows trimmed
  from work.oda_ci_probe;
quit;
%put NOTE: ODA_CI_PROBE_ROWS=&oda_ci_probe_rows;
'''
        result = sas.submit(program, results="TEXT")
        log = str(result.get("LOG", ""))
        errors = _sas_error_lines(log)
        if errors:
            raise RuntimeError(
                f"SAS ODA probe returned {len(errors)} SAS ERROR line(s); first="
                + errors[0][:240]
            )

        frame = sas.sd2df(table="oda_ci_probe", libref="work")
        frame.columns = [str(column).upper() for column in frame.columns]
        expected_columns = {"PROBE_ID", "PROBE_VALUE", "EXECUTION_SOURCE"}
        missing = expected_columns.difference(frame.columns)
        if missing:
            raise RuntimeError(f"SAS ODA probe output is missing columns: {sorted(missing)}")
        if len(frame) != 3:
            raise RuntimeError(f"SAS ODA probe expected 3 rows, received {len(frame)}")

        ids = pd.to_numeric(frame["PROBE_ID"], errors="raise").astype(int).tolist()
        values = pd.to_numeric(frame["PROBE_VALUE"], errors="raise").astype(int).tolist()
        sources = frame["EXECUTION_SOURCE"].astype(str).str.strip().tolist()
        if ids != [1, 2, 3] or values != [10, 20, 30]:
            raise RuntimeError(f"unexpected SAS round-trip values: ids={ids}, values={values}")
        if sources != ["GITHUB_ACTIONS_SASPY"] * 3:
            raise RuntimeError("unexpected execution_source values returned by SAS ODA")

        frame.to_csv(outputs / "sas_oda_probe.csv", index=False)
        metrics = {
            "version": "0.26.1-probe",
            "sas_oda_connected": True,
            "sas_program_executed": True,
            "sas_dataset_roundtrip": True,
            "probe_rows": int(len(frame)),
            "probe_values": values,
            "runtime_status": "EXECUTED_SAS_ODA_CONNECTIVITY_PROBE",
            "evidence_boundary": (
                "Connectivity and deterministic SAS execution probe only; this does not yet "
                "claim execution or validation of the v0.26 clinical-programming packages."
            ),
        }
        (outputs / "sas_oda_probe_metrics.json").write_text(
            json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (outputs / "sas_oda_probe_summary.md").write_text(
            "# SAS ODA CI connectivity probe\n\n"
            "- SAS ODA connection: **PASS**\n"
            "- SAS program execution: **PASS**\n"
            "- SAS dataset -> pandas round-trip: **PASS**\n"
            "- deterministic rows: **3/3 PASS**\n"
            "- runtime status: **`EXECUTED_SAS_ODA_CONNECTIVITY_PROBE`**\n\n"
            "This probe validates connectivity and real SAS execution only. Full ADSL/ADAE/TFL/MMRM "
            "reconciliation remains a separate controlled upgrade.\n",
            encoding="utf-8",
        )
        print("SAS ODA connectivity probe PASS: real SAS execution and dataset round-trip succeeded.")
    finally:
        if sas is not None:
            try:
                sas.endsas()
            except Exception:
                pass


if __name__ == "__main__":
    main()
