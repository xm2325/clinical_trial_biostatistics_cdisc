import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.efficacy import (  # noqa: E402
    acitm01_week24_ancova,
    derive_acitm01_adqs_style,
    derive_adqscibc_style,
)
from cdisc_portfolio.io import read_dataset_json  # noqa: E402
from cdisc_portfolio.reference import compare_adqscibc_reference  # noqa: E402


def _adsl():
    arms = ["Placebo", "Xanomeline Low Dose", "Xanomeline High Dose"] * 2
    return pd.DataFrame([
        {
            "STUDYID": "S", "USUBJID": str(i + 1), "TRT01P": arm, "TRT01A": arm,
            "RANDFL": "Y", "COMPLFL": "Y" if i != 1 else "N",
        }
        for i, arm in enumerate(arms)
    ])


def test_cibic_windowing_and_locf():
    adsl = _adsl().iloc[:1].copy()
    qs = pd.DataFrame([
        {"STUDYID":"S","USUBJID":"1","QSSEQ":6001,"QSTESTCD":"CIBICVAL","QSSTRESN":3,"QSDY":29,"QSDTC":"2020-01-29","VISIT":"WEEK 4","VISITNUM":5},
        {"STUDYID":"S","USUBJID":"1","QSSEQ":6002,"QSTESTCD":"CIBICVAL","QSSTRESN":5,"QSDY":198,"QSDTC":"2020-07-17","VISIT":"RETRIEVAL","VISITNUM":201},
    ])
    out = derive_adqscibc_style(qs, adsl).set_index("AVISIT")
    assert out.loc["Week 8", "AVAL"] == 3
    assert out.loc["Week 16", "AVAL"] == 3
    assert out.loc["Week 16", "DTYPE"] == "LOCF"
    assert out.loc["Week 24", "AVAL"] == 5
    assert out.loc["Week 24", "DTYPE"] == ""


def test_acitm01_derivation_and_ancova():
    rows = []
    seq = 1
    pairs = [(3,2),(4,2),(5,2),(2,3),(3,1),(4,1)]
    for uid, (base, wk24) in enumerate(pairs, start=1):
        rows.extend([
            {"STUDYID":"S","USUBJID":str(uid),"QSSEQ":seq,"QSTESTCD":"ACITM01","QSTEST":"WORD RECALL TASK","QSSTRESN":base,"QSBLFL":"Y","QSDY":1,"QSDTC":"2020-01-01","VISIT":"BASELINE","VISITNUM":3},
            {"STUDYID":"S","USUBJID":str(uid),"QSSEQ":seq+1,"QSTESTCD":"ACITM01","QSTEST":"WORD RECALL TASK","QSSTRESN":wk24,"QSBLFL":"","QSDY":168,"QSDTC":"2020-06-17","VISIT":"WEEK 24","VISITNUM":12},
        ])
        seq += 10
    adqs = derive_acitm01_adqs_style(pd.DataFrame(rows), _adsl())
    assert int(adqs["ABLFL"].eq("Y").sum()) == 6
    assert (adqs.loc[adqs["ABLFL"].ne("Y"), "CHG"] == adqs.loc[adqs["ABLFL"].ne("Y"), "AVAL"] - adqs.loc[adqs["ABLFL"].ne("Y"), "BASE"]).all()
    lsmeans, contrasts, subjects = acitm01_week24_ancova(adqs)
    assert len(lsmeans) == 6
    assert len(contrasts) == 4
    assert subjects.loc[subjects["analysis"].eq("Observed Week 24"), "USUBJID"].nunique() == 6


def test_reference_comparison_exact_match():
    derived = pd.DataFrame([
        {"USUBJID":"1","AVISIT":"Week 8","AVAL":4,"DTYPE":"","QSSEQ":6001},
        {"USUBJID":"1","AVISIT":"Week 16","AVAL":4,"DTYPE":"LOCF","QSSEQ":6001},
    ])
    reference = derived.assign(ANL01FL="Y")
    metrics, detail = compare_adqscibc_reference(derived, reference)
    assert metrics.loc[0, "reference_key_coverage"] == 1.0
    assert metrics.loc[0, "aval_match_rate_on_overlap"] == 1.0
    assert metrics.loc[0, "dtype_match_rate_on_overlap"] == 1.0
    assert detail["AVAL_MATCH"].all()


def test_dataset_json_reader(tmp_path):
    payload = {
        "columns": [{"name":"A"}, {"name":"B"}],
        "rows": [[1, "x"], [2, "y"]],
    }
    path = tmp_path / "tiny.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    df = read_dataset_json(path)
    assert df.to_dict(orient="records") == [{"A":1,"B":"x"},{"A":2,"B":"y"}]
