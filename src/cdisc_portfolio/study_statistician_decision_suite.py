from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_study_statistician_decision_suite(root: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    cfg = _load_json(root / "spec" / "study_statistician_decision_suite_v0_24.json")
    rows: list[dict[str, object]] = []
    for component in cfg["components"]:
        path = root / str(component["metrics"])
        if not path.exists():
            raise FileNotFoundError(f"Missing decision-suite component metrics: {path}")
        metrics = _load_json(path)
        claim_ok = metrics.get("claim") == component["required_claim"]
        version_ok = metrics.get("version") == cfg["version"]
        pass_ok = metrics.get("all_passed") is True
        rows.append({
            "component": component["id"],
            "required_claim": component["required_claim"],
            "observed_claim": metrics.get("claim"),
            "version": metrics.get("version"),
            "claim_matches": claim_ok,
            "version_matches": version_ok,
            "component_all_passed": pass_ok,
            "passed": bool(claim_ok and version_ok and pass_ok),
        })

    closure_path = root / str(cfg["inherited_closure"])
    if not closure_path.exists():
        raise FileNotFoundError(f"Missing inherited analysis-closure metrics: {closure_path}")
    closure = _load_json(closure_path)
    closure_ok = closure.get("all_passed") is True
    rows.append({
        "component": "inherited_v0_23_analysis_closure",
        "required_claim": "PORTFOLIO_EVIDENCE_CLOSURE_COMPLETE",
        "observed_claim": closure.get("closure_claim"),
        "version": closure.get("version", "inherited"),
        "claim_matches": closure.get("closure_claim") == "PORTFOLIO_EVIDENCE_CLOSURE_COMPLETE",
        "version_matches": True,
        "component_all_passed": closure_ok,
        "passed": bool(closure_ok and closure.get("closure_claim") == "PORTFOLIO_EVIDENCE_CLOSURE_COMPLETE"),
    })

    checks = pd.DataFrame(rows)
    metrics = {
        "version": cfg["version"],
        "claim": cfg["claim"],
        "component_count": int(len(cfg["components"])),
        "inherited_closure_checked": True,
        "checks_passed": int(checks["passed"].sum()),
        "checks_total": int(len(checks)),
        "all_passed": bool(checks["passed"].all()),
    }
    return checks, metrics


def write_study_statistician_decision_suite(root: Path) -> dict[str, object]:
    checks, metrics = run_study_statistician_decision_suite(root)
    out = root / "outputs"
    checks.to_csv(out / "study_statistician_decision_suite_qc.csv", index=False)
    (out / "study_statistician_decision_suite_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary = [
        "# Study Statistician decision suite",
        "",
        f"- Controlled claim: `{metrics['claim']}`.",
        f"- New v0.24 decision components: {metrics['component_count']}.",
        f"- Suite checks including inherited v0.23 closure: {metrics['checks_passed']}/{metrics['checks_total']} PASS.",
        "",
        "The suite intentionally links three different statistical decisions: prospective operating-characteristics stress testing, actual-treatment safety-population review, and rejection of an outcome-driven post-data-review switch from the controlled primary MMRM to supportive reference-based MI. It is additive to the inherited T01-T25 evidence package and does not create a new TLF or sponsor/regulatory claim.",
    ]
    (out / "study_statistician_decision_suite_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    if not metrics["all_passed"]:
        raise RuntimeError("Study Statistician decision-suite gate failed")
    return metrics
