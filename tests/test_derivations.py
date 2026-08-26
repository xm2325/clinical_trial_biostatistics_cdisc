import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.derive import derive_adsl_style, derive_adae_style


def _dm():
    return pd.DataFrame([
        {"STUDYID":"S","USUBJID":"1","AGE":60,"SEX":"F","RACE":"WHITE","COUNTRY":"USA","ARM":"Placebo","ACTARM":"Placebo","RFXSTDTC":"2020-01-01","RFXENDTC":"2020-01-10"},
        {"STUDYID":"S","USUBJID":"2","AGE":61,"SEX":"M","RACE":"WHITE","COUNTRY":"USA","ARM":"Xanomeline Low Dose","ACTARM":"Xanomeline Low Dose","RFXSTDTC":"2020-01-02","RFXENDTC":"2020-01-12"},
        {"STUDYID":"S","USUBJID":"3","AGE":62,"SEX":"F","RACE":"WHITE","COUNTRY":"USA","ARM":"Screen Failure","ACTARM":"Screen Failure","RFXSTDTC":None,"RFXENDTC":None},
    ])


def _ex():
    return pd.DataFrame([
        {"STUDYID":"S","USUBJID":"1","EXSEQ":1,"EXTRT":"PLACEBO","EXDOSE":0,"EXSTDTC":"2020-01-01","EXENDTC":"2020-01-05"},
        {"STUDYID":"S","USUBJID":"1","EXSEQ":2,"EXTRT":"PLACEBO","EXDOSE":0,"EXSTDTC":"2020-01-06","EXENDTC":"2020-01-10"},
        {"STUDYID":"S","USUBJID":"2","EXSEQ":1,"EXTRT":"XANOMELINE","EXDOSE":54,"EXSTDTC":"2020-01-02","EXENDTC":"2020-01-12"},
    ])


def _ds():
    return pd.DataFrame([
        {"STUDYID":"S","USUBJID":"1","DSSEQ":1,"DSTERM":"RANDOMIZED","DSDECOD":"RANDOMIZED","DSCAT":"PROTOCOL MILESTONE","DSSTDTC":"2020-01-01"},
        {"STUDYID":"S","USUBJID":"1","DSSEQ":2,"DSTERM":"PROTOCOL COMPLETED","DSDECOD":"COMPLETED","DSCAT":"DISPOSITION EVENT","DSSTDTC":"2020-01-10"},
        {"STUDYID":"S","USUBJID":"2","DSSEQ":1,"DSTERM":"RANDOMIZED","DSDECOD":"RANDOMIZED","DSCAT":"PROTOCOL MILESTONE","DSSTDTC":"2020-01-02"},
        {"STUDYID":"S","USUBJID":"2","DSSEQ":2,"DSTERM":"ADVERSE EVENT","DSDECOD":"ADVERSE EVENT","DSCAT":"DISPOSITION EVENT","DSSTDTC":"2020-01-12"},
        {"STUDYID":"S","USUBJID":"3","DSSEQ":1,"DSTERM":"SCREEN FAILURE","DSDECOD":"SCREEN FAILURE","DSCAT":"DISPOSITION EVENT","DSSTDTC":"2020-01-01"},
    ])


def test_adsl_uses_observed_exposure_and_disposition():
    adsl = derive_adsl_style(_dm(), _ex(), _ds()).set_index("USUBJID")
    assert adsl.loc["1", "SAFFL"] == "Y"
    assert adsl.loc["3", "SAFFL"] == "N"
    assert adsl.loc["1", "COMPLFL"] == "Y"
    assert adsl.loc["2", "DCSFL"] == "Y"
    assert adsl.loc["2", "EOSDECOD"] == "ADVERSE EVENT"
    assert adsl.loc["1", "EXDURN_RAW"] == 10
    assert adsl.loc["1", "TRTDURN"] == 10
    assert adsl.loc["1", "EXN"] == 2
    assert adsl.loc["1", "TRTEDTSRC"] == "EX"


def test_adae_teae_window_and_flags():
    adsl = derive_adsl_style(_dm(), _ex(), _ds())
    ae = pd.DataFrame([
        {"STUDYID":"S","USUBJID":"1","AESEQ":1,"AETERM":"pre","AEDECOD":"HEADACHE","AEBODSYS":"NERVOUS","AESEV":"MILD","AESER":"N","AEREL":"NONE","AEOUT":"RECOVERED","AESTDTC":"2019-12-31","AEENDTC":"2020-01-01"},
        {"STUDYID":"S","USUBJID":"1","AESEQ":2,"AETERM":"on","AEDECOD":"RASH","AEBODSYS":"SKIN","AESEV":"MODERATE","AESER":"N","AEREL":"POSSIBLE","AEOUT":"RECOVERED","AESTDTC":"2020-01-05","AEENDTC":"2020-01-07"},
        {"STUDYID":"S","USUBJID":"1","AESEQ":3,"AETERM":"late","AEDECOD":"NAUSEA","AEBODSYS":"GI","AESEV":"SEVERE","AESER":"Y","AEREL":"PROBABLE","AEOUT":"RECOVERED","AESTDTC":"2020-02-10","AEENDTC":"2020-02-11"},
    ])
    adae = derive_adae_style(ae, adsl).set_index("AESEQ")
    assert adae.loc[1, "TRTEMFL"] == ""
    assert adae.loc[2, "TRTEMFL"] == "Y"
    assert adae.loc[2, "RELFL"] == "Y"
    assert adae.loc[2, "MODSEVFL"] == "Y"
    assert adae.loc[3, "TRTEMFL"] == ""
    assert set(adae["TRTEMFL"].unique()).issubset({"Y", ""})


def test_missing_exposure_end_uses_disposition_date_with_flag():
    dm = _dm().iloc[[0]].copy()
    dm.loc[:, "RFXENDTC"] = None
    ex = _ex().iloc[[0]].copy()
    ex.loc[:, "EXENDTC"] = None
    ds = _ds().loc[_ds()["USUBJID"].eq("1")].copy()
    adsl = derive_adsl_style(dm, ex, ds).iloc[0]
    assert str(adsl["TRTEDT"].date()) == "2020-01-10"
    assert adsl["TRTEDTSRC"] == "DS_DISPOSITION_FALLBACK"
    assert adsl["TRTDURN"] == 10
