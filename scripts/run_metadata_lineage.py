from pathlib import Path
from cdisc_portfolio.metadata_lineage import write_metadata_outputs

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    metrics = write_metadata_outputs(root)
    print(
        f"metadata lineage: datasets={metrics['datasets']}; "
        f"variables={metrics['variables_with_exact_coverage']}/{metrics['actual_variables']}; "
        f"analysis refs={metrics['analysis_dataset_references_resolved']}/{metrics['analysis_dataset_references']}; "
        f"xml variables={metrics['xml_variable_defs']}; passed={metrics['all_passed']}"
    )
