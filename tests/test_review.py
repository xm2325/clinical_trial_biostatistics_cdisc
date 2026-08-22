import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.review import (
    check_adae_adsl_consistency,
    check_mmrm_source_consistency,
    check_safety_table_denominators,
)


def _adsl() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "STUDYID": ["S1", "S1"],
            "USUBJID": ["01", "02"],
            "TRT01A": ["Placebo", "Active"],
            "SAFFL": ["Y", "Y"],
            "TRTSDT": ["2026-01-01", "2026-01-01"],
            "TRTEDT": ["2026-01-30", "2026-01-30"],
        }
    )


def test_adae_review_accepts_consistent_subject_attributes():
    adae = pd.DataFrame(
        {
            "STUDYID": ["S1", "S1"],
            "USUBJID": ["01", "02"],
            "TRT01A": ["Placebo", "Active"],
            "SAFFL": ["Y", "Y"],
            "TRTSDT": ["2026-01-01", "2026-01-01"],
            "TRTEDT": ["2026-01-30", "2026-01-30"],
        }
    )
    passed, _ = check_adae_adsl_consistency(_adsl(), adae)
    assert passed


def test_adae_review_detects_treatment_mismatch():
    adae = pd.DataFrame(
        {
            "STUDYID": ["S1", "S1"],
            "USUBJID": ["01", "02"],
            "TRT01A": ["Placebo", "Placebo"],
            "SAFFL": ["Y", "Y"],
            "TRTSDT": ["2026-01-01", "2026-01-01"],
            "TRTEDT": ["2026-01-30", "2026-01-30"],
        }
    )
    passed, detail = check_adae_adsl_consistency(_adsl(), adae)
    assert not passed
    assert "treatment mismatch=1" in detail


def test_safety_denominator_review_detects_corrupted_tlf_denominator():
    table5 = pd.DataFrame(
        {
            "TRT01A": ["Placebo", "Active"],
            "denom": [2, 1],
        }
    )
    table6 = pd.DataFrame(
        {
            "TRT01A": ["Placebo", "Active"],
            "denom": [1, 1],
        }
    )
    passed, detail = check_safety_table_denominators(_adsl(), table5, table6)
    assert not passed
    assert "table5 bad denominators=1" in detail


def test_mmrm_review_detects_source_value_corruption():
    adqs = pd.DataFrame(
        {
            "STUDYID": ["S1"],
            "USUBJID": ["01"],
            "QSSEQ": [10],
            "TRT01A": ["Placebo"],
            "AVAL": [20.0],
            "BASE": [18.0],
            "CHG": [2.0],
        }
    )
    mmrm = adqs.copy()
    mmrm.loc[0, "CHG"] = 3.0
    passed, detail = check_mmrm_source_consistency(adqs, mmrm)
    assert not passed
    assert "numeric field mismatches=1" in detail
