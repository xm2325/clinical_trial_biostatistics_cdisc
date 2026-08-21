import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.qc import run_qc


def test_required_qc_passes_clean_fixture():
    adsl = pd.DataFrame([
        {"STUDYID":"S","USUBJID":"1","SAFFL":"Y","EXN":1,"TRTSDT":pd.Timestamp("2020-01-01"),"TRTEDT":pd.Timestamp("2020-01-10"),"RANDFL":"Y","EOSDECOD":"COMPLETED","COMPLFL":"Y","DCSFL":"N"}
    ])
    adae = pd.DataFrame([
        {"STUDYID":"S","USUBJID":"1","AESEQ":1,"SAFFL":"Y","TRTEMFL":"Y","ASTDT":pd.Timestamp("2020-01-05"),"TRTSDT":pd.Timestamp("2020-01-01"),"TRTEDT":pd.Timestamp("2020-01-10")}
    ])
    qc = run_qc(adsl, adae)
    required = qc.loc[qc["required"]]
    assert required["passed"].all()
