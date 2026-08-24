from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.analysis_readiness import write_analysis_closure_outputs
from cdisc_portfolio.csr_interpretation import write_csr_interpretation_outputs
from cdisc_portfolio.csr_interpretation_extension import write_csr_interpretation_extension_outputs


def main() -> None:
    closure = write_analysis_closure_outputs(ROOT)
    print(
        "Analysis closure: "
        f"checks={closure['closure_checks_passed']}/{closure['closure_checks']}; "
        f"known_issues={closure['readiness_known_issues']}; "
        f"blocking_open={closure['readiness_blocking_open_issues']}; "
        f"passed={closure['all_passed']}"
    )

    interpretation = write_csr_interpretation_outputs(ROOT)
    extension = write_csr_interpretation_extension_outputs(ROOT)
    print(
        "CSR interpretation: "
        f"primary_rejections={interpretation['primary_familywise_rejections']}/{interpretation['primary_hypotheses']}; "
        f"sensitivity_mcse={interpretation['reference_based_mcse_passed']}/{interpretation['reference_based_rows']}; "
        f"base_rows={interpretation['conclusion_rows']}; "
        f"fixed_delta_rows={extension['fixed_delta_conclusion_rows']}; "
        f"checks={interpretation['required_checks_passed']}/{interpretation['required_checks']}+"
        f"{extension['required_checks_passed']}/{extension['required_checks']}; "
        f"passed={interpretation['all_passed'] and extension['all_passed']}"
    )


if __name__ == "__main__":
    main()
