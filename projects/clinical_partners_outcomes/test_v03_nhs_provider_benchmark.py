import pandas as pd

from v03_nhs_provider_benchmark import clean_nhs, provider_panel


def test_provider_panel_uses_provider_rollup_and_parses_suppression():
    df = pd.DataFrame({
        "REPORTING_PERIOD_START": ["2026-06-01"] * 4,
        "REPORTING_PERIOD_END": ["2026-06-30"] * 4,
        "GROUP_TYPE": ["Provider", "Provider", "England", "Provider"],
        "ORG_CODE1": ["all", "all", "all", "all"],
        "ORG_NAME1": ["all SubICBs", "all SubICBs", "all", "all SubICBs"],
        "ORG_CODE2": ["P1", "P1", "all", "P2"],
        "ORG_NAME2": ["Provider One", "Provider One", "all Providers", "Provider Two"],
        "MEASURE_ID": ["M186", "M195", "M186", "M186"],
        "MEASURE_NAME": [
            "Percentage_ReliableImprovement",
            "Percentage_ReliableRecovery",
            "Percentage_ReliableImprovement",
            "Percentage_ReliableImprovement",
        ],
        "MEASURE_VALUE": ["70.1", "48.2", "68.5", "*"],
    })
    clean = clean_nhs(df)
    assert clean["value"].isna().sum() == 1
    panel = provider_panel(clean)
    assert set(panel["provider_code"]) == {"P1", "P2"}
    assert "all" not in set(panel["provider_code"])
    assert panel.loc[panel["provider_code"].eq("P2"), "suppressed_or_non_numeric"].iloc[0]
