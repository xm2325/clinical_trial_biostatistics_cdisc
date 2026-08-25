from pathlib import Path

p = Path("README.md")
s = p.read_text(encoding="utf-8")
s = s.replace("docs/mi_randomised_assignment_repair_v0_23.md", "docs/randomised_treatment_assignment_repair.md")
s = s.replace("## Key v0.22 and inherited files", "## Key v0.23 and inherited files", 1)
marker = "```text\nspec/statistical_review_queries_v0_22.json"
if "spec/mi_assignment_v0_23.json" not in s:
    block = """```text
spec/mi_assignment_v0_23.json                            assignment and MI-boundary contract
spec/change_impact_graph_v0_23_extension.json            CR-015 dependency extension
spec/change_requests_v0_23_extension.json                CR-015 controlled repair record
src/cdisc_portfolio/mi_assignment.py                      subject-level assignment audit and planned MI inputs
src/cdisc_portfolio/change_control_v023.py               layered v0.23 change-control merger
scripts/run_mi_assignment_inputs.py                       planned-assignment MI staging
scripts/run_mi_assignment_audit.py                        assignment audit runner
scripts/restore_mi_assignment_inputs.py                   post-MI input restoration
tests/test_mi_assignment.py                               assignment/population negative controls
tests/test_change_control_v023.py                         CR-015 propagation negative controls
docs/randomised_treatment_assignment_repair.md            repair rationale and evidence boundary

spec/statistical_review_queries_v0_22.json"""
    if marker not in s:
        raise SystemExit("README key-files marker not found")
    s = s.replace(marker, block, 1)
p.write_text(s, encoding="utf-8")
print("v0.23 README references fixed")
