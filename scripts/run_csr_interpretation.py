from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.csr_interpretation import write_csr_interpretation_outputs


def main() -> None:
    metrics = write_csr_interpretation_outputs(ROOT)
    print(
        "CSR interpretation: "
        f"primary_rejections={metrics['primary_familywise_rejections']}/{metrics['primary_hypotheses']}; "
        f"sensitivity_mcse={metrics['reference_based_mcse_passed']}/{metrics['reference_based_rows']}; "
        f"conclusion_rows={metrics['conclusion_rows']}; "
        f"checks={metrics['required_checks_passed']}/{metrics['required_checks']}; "
        f"passed={metrics['all_passed']}"
    )


if __name__ == "__main__":
    main()
