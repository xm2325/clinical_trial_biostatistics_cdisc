from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.bms_statistical_programming import write_bms_statistical_programming_outputs


def main() -> None:
    metrics = write_bms_statistical_programming_outputs(ROOT)
    print(
        "BMS statistical-programming evidence: "
        f"SAS={metrics['sas_programs_static_review_passed']}/{metrics['sas_programs']}; "
        f"datasets={metrics['analysis_datasets']}; "
        f"DDT_variables={metrics['analysis_dataset_variables']}; "
        f"DefineXML={metrics['define_xml_candidate_datasets']}/{metrics['define_xml_candidate_variables']}; "
        f"checks={metrics['required_checks_passed']}/{metrics['required_checks']}; "
        f"SAS_runtime={metrics['sas_runtime_status']}; "
        f"P21={metrics['pinnacle21_status']}; "
        f"passed={metrics['all_required_passed']}"
    )


if __name__ == "__main__":
    main()
