import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("learning", ROOT / "scripts" / "build_cdisc_learning_examples.py")
learning = importlib.util.module_from_spec(spec)
spec.loader.exec_module(learning)


def test_kaplan_meier_simple():
    t, s, med = learning.kaplan_meier(np.array([1, 2, 3, 4]), np.array([1, 1, 0, 1]))
    assert list(t) == [0.0, 1.0, 2.0, 4.0]
    assert np.allclose(s, [1.0, 0.75, 0.5, 0.0])
    assert med == 2.0


def test_logrank_identical_groups_is_null():
    time = np.array([1, 2, 3, 4, 1, 2, 3, 4], dtype=float)
    event = np.array([1, 1, 0, 1, 1, 1, 0, 1])
    group = np.array(["A"] * 4 + ["B"] * 4)
    chi2, p = learning.logrank(time, event, group)
    assert abs(chi2) < 1e-12 and p > 0.99


def test_rederive_adsl_imputes_open_last_exposure():
    dm = pd.DataFrame({"USUBJID": ["1", "2"], "ARMCD": ["Pbo", "Pbo"], "ARM": ["Placebo", "Placebo"],
                       "AGE": [64, 81], "RFENDTC": ["2020-01-31", "2020-02-10"]})
    ex = pd.DataFrame({"USUBJID": ["1", "2", "2"], "EXSTDTC": ["2020-01-01", "2020-01-01", "2020-01-15"],
                       "EXENDTC": ["2020-01-31", "2020-01-14", np.nan]})
    adsl = pd.DataFrame({"USUBJID": ["1", "2"], "AGEGR1": ["<65", ">80"], "SAFFL": ["Y", "Y"],
                         "TRTSDT": ["2020-01-01", "2020-01-01"], "TRTEDT": ["2020-01-31", "2020-02-10"],
                         "TRTDUR": [31, 41]})
    tab, st = learning.rederive_adsl(dm, ex, adsl)
    assert st["open_last_exposure_subjects"] == ["2"]
    v1 = tab[(tab["变量"] == "TRTEDT") & tab["推导规则"].str.startswith("v1")].iloc[0]
    v2 = tab[(tab["变量"] == "TRTEDT") & tab["推导规则"].str.startswith("v2")].iloc[0]
    assert (v1["不一致"], v2["不一致"]) == (1, 0)
