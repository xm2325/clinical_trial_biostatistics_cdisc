import copy

import pandas as pd
import pytest

from cdisc_portfolio.tte import derive_retention_adtte


ARMS = ["Placebo", "Xanomeline Low Dose", "Xanomeline High Dose"]


def _spec():
    return {
        "version": "0.17.0",
        "parameter": {
            "PARAM": "Time to Study Discontinuation (days)",
            "PARAMCD": "TTDISC",
            "origin_variable": "TRTSDT",
            "event_or_censor_variable": "EOSDT",
        },
        "population": {
            "randomised_flag": "RANDFL",
            "required_value": "Y",
            "treatment_arms": ARMS,
        },
        "event_rule": {
            "condition_variable": "DCSFL",
            "condition_value": "Y",
            "CNSR": 0,
            "description_source": "EOSDECOD",
        },
        "censor_rule": {
            "condition_variable": "COMPLFL",
            "condition_value": "Y",
            "CNSR": 1,
            "EVNTDESC": "STUDY COMPLETED",
        },
    }


def _adsl():
    return pd.DataFrame(
        [
            {
                "STUDYID": "S1",
                "USUBJID": "01",
                "TRT01P": "Placebo",
                "TRT01A": "Placebo",
                "SAFFL": "Y",
                "RANDFL": "Y",
                "TRTSDT": "2026-01-01",
                "EOSDT": "2026-06-30",
                "DCSFL": "N",
                "COMPLFL": "Y",
                "EOSDECOD": "COMPLETED",
                "EOSTERM": "PROTOCOL COMPLETED",
            },
            {
                "STUDYID": "S1",
                "USUBJID": "02",
                "TRT01P": "Xanomeline Low Dose",
                "TRT01A": "Xanomeline Low Dose",
                "SAFFL": "Y",
                "RANDFL": "Y",
                "TRTSDT": "2026-01-03",
                "EOSDT": "2026-02-01",
                "DCSFL": "Y",
                "COMPLFL": "N",
                "EOSDECOD": "ADVERSE EVENT",
                "EOSTERM": "ADVERSE EVENT",
            },
            {
                "STUDYID": "S1",
                "USUBJID": "03",
                "TRT01P": "Xanomeline High Dose",
                "TRT01A": "Xanomeline High Dose",
                "SAFFL": "Y",
                "RANDFL": "Y",
                "TRTSDT": "2026-01-05",
                "EOSDT": "2026-03-05",
                "DCSFL": "Y",
                "COMPLFL": "N",
                "EOSDECOD": "WITHDRAWAL BY SUBJECT",
                "EOSTERM": "WITHDRAWAL BY SUBJECT",
            },
            {
                "STUDYID": "S1",
                "USUBJID": "04",
                "TRT01P": "Screen Failure",
                "TRT01A": "Screen Failure",
                "SAFFL": "N",
                "RANDFL": "N",
                "TRTSDT": None,
                "EOSDT": "2026-01-10",
                "DCSFL": "N",
                "COMPLFL": "N",
                "EOSDECOD": "SCREEN FAILURE",
                "EOSTERM": "SCREEN FAILURE",
            },
        ]
    )


def test_retention_adtte_derives_event_censor_and_duration():
    result = derive_retention_adtte(_adsl(), _spec())
    assert result.metrics["all_required_passed"] is True
    assert result.metrics["subjects"] == 3
    assert result.metrics["events"] == 2
    assert result.metrics["censored"] == 1
    out = result.dataset.set_index("USUBJID")
    assert out.loc["01", "CNSR"] == 1
    assert out.loc["01", "EVNTDESC"] == "STUDY COMPLETED"
    assert out.loc["02", "CNSR"] == 0
    assert out.loc["02", "EVNTDESC"] == "ADVERSE EVENT"
    assert out.loc["02", "AVAL"] == 30
    assert out.loc["03", "AVAL"] == 60
    assert out.loc["02", "PARAMCD"] == "TTDISC"
    assert out.loc["02", "STARTSRC"] == "ADSL.TRTSDT"
    assert out.loc["02", "ADTSRC"] == "ADSL.EOSDT"


def test_retention_adtte_fails_partition_when_discontinued_and_completed():
    adsl = _adsl()
    adsl.loc[1, "COMPLFL"] = "Y"
    result = derive_retention_adtte(adsl, _spec())
    assert result.metrics["all_required_passed"] is False
    failed = result.qc.loc[~result.qc["passed"], "check"].tolist()
    assert "Discontinuation and completion flags form an exact partition" in failed


def test_retention_adtte_fails_negative_duration():
    adsl = _adsl()
    adsl.loc[1, "EOSDT"] = "2025-12-31"
    result = derive_retention_adtte(adsl, _spec())
    assert result.metrics["all_required_passed"] is False
    failed = result.qc.loc[~result.qc["passed"], "check"].tolist()
    assert "Retention analysis dates are on or after origin dates" in failed


def test_retention_adtte_fails_missing_origin_date():
    adsl = _adsl()
    adsl.loc[1, "TRTSDT"] = None
    result = derive_retention_adtte(adsl, _spec())
    assert result.metrics["all_required_passed"] is False
    failed = result.qc.loc[~result.qc["passed"], "check"].tolist()
    assert "Retention origin dates are complete" in failed


def test_retention_adtte_rejects_wrong_censor_codes():
    spec = copy.deepcopy(_spec())
    spec["censor_rule"]["CNSR"] = 0
    with pytest.raises(ValueError, match="CNSR=0 for events and CNSR=1"):
        derive_retention_adtte(_adsl(), spec)


def test_retention_adtte_rejects_missing_required_column():
    with pytest.raises(ValueError, match="missing required columns"):
        derive_retention_adtte(_adsl().drop(columns=["EOSDT"]), _spec())
