from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.analysis_readiness import write_analysis_closure_outputs
from cdisc_portfolio.csr_interpretation import write_csr_interpretation_outputs
from cdisc_portfolio.csr_interpretation_extension import write_csr_interpretation_extension_outputs
from cdisc_portfolio.statistical_review_queries import write_statistical_review_query_outputs


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

    review = write_statistical_review_query_outputs(ROOT)
    print(
        "Statistical review responses: "
        f"queries={review['query_rows']}; "
        f"week24_missing={review['week24_missing']}/{review['week24_randomized']}; "
        f"mismatches={review['planned_actual_treatment_mismatches']}; "
        f"checks={review['required_checks_passed']}/{review['required_checks']}; "
        f"passed={review['all_passed']}"
    )

    # v0.25 clinical-programming release gate. This runs after the existing
    # change-control and SAP-to-TLF traceability steps, so it can require those
    # controlled release signals as part of the programming package.
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_clinical_programming_workflow.py")],
        check=True,
    )


if __name__ == "__main__":
    main()
