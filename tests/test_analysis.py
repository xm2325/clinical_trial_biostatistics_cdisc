import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.analysis import teae_risk_differences
from cdisc_portfolio.sample_size import two_arm_binary_n_per_arm, two_arm_continuous_n_per_arm


def test_teae_risk_difference_direction():
    adsl = pd.DataFrame([
        {"USUBJID":"P1","TRT01A":"Placebo","SAFFL":"Y"},
        {"USUBJID":"P2","TRT01A":"Placebo","SAFFL":"Y"},
        {"USUBJID":"X1","TRT01A":"Xanomeline Low Dose","SAFFL":"Y"},
        {"USUBJID":"X2","TRT01A":"Xanomeline Low Dose","SAFFL":"Y"},
    ])
    adae = pd.DataFrame([
        {"USUBJID":"P1","TRTEMFL":"Y"},
        {"USUBJID":"X1","TRTEMFL":"Y"},
        {"USUBJID":"X2","TRTEMFL":"Y"},
    ])
    out = teae_risk_differences(adsl, adae)
    assert len(out) == 1
    assert out.iloc[0]["risk_difference"] == 0.5


def test_sample_size_examples_are_positive_and_power_sensitive():
    n80 = two_arm_continuous_n_per_arm(effect=3, sd=10, power=.80)
    n90 = two_arm_continuous_n_per_arm(effect=3, sd=10, power=.90)
    assert n90 > n80 > 0
    assert two_arm_binary_n_per_arm(.30, .20, power=.90) > 0
