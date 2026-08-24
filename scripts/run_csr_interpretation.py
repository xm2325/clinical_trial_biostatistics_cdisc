from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.csr_interpretation import write_csr_interpretation_outputs
from cdisc_portfolio.csr_interpretation_extension import write_csr_interpretation_extension_outputs


def main() -> None:
    base = write_csr_interpretation_outputs(ROOT)
    extension = write_csr_interpretation_extension_outputs(ROOT)
    print(
        "CSR interpretation: "
        f"primary_rejections={base['primary_familywise_rejections']}/{base['primary_hypotheses']}; "
        f"sensitivity_mcse={base['reference_based_mcse_passed']}/{base['reference_based_rows']}; "
        f"base_rows={base['conclusion_rows']}; fixed_delta_rows={extension['fixed_delta_conclusion_rows']}; "
        f"checks={base['required_checks_passed']}/{base['required_checks']}+"
        f"{extension['required_checks_passed']}/{extension['required_checks']}; "
        f"passed={base['all_passed'] and extension['all_passed']}"
    )


if __name__ == "__main__":
    main()
