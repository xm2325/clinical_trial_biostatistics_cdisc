from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


IMPACT_CATEGORIES = (
    "analysis_datasets",
    "tlfs",
    "qc",
    "documents",
    "specs",
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_impact_graph(graph: dict[str, Any]) -> None:
    components = graph.get("components")
    if not isinstance(components, dict) or not components:
        raise ValueError("change-impact graph must contain non-empty components")

    for name, node in components.items():
        if not isinstance(node, dict):
            raise ValueError(f"component {name!r} must be an object")
        downstream = node.get("downstream", [])
        if not isinstance(downstream, list) or len(downstream) != len(set(downstream)):
            raise ValueError(f"component {name!r} has invalid/duplicate downstream entries")
        unknown = sorted(set(downstream) - set(components))
        if unknown:
            raise ValueError(f"component {name!r} references unknown downstream components {unknown}")
        impacts = node.get("impacts", {})
        if not isinstance(impacts, dict):
            raise ValueError(f"component {name!r} impacts must be an object")
        unknown_categories = sorted(set(impacts) - set(IMPACT_CATEGORIES))
        if unknown_categories:
            raise ValueError(f"component {name!r} uses unknown impact categories {unknown_categories}")
        for category, resources in impacts.items():
            if not isinstance(resources, list) or any(not isinstance(x, str) or not x for x in resources):
                raise ValueError(f"component {name!r} category {category!r} must be a list of non-empty strings")
            if len(resources) != len(set(resources)):
                raise ValueError(f"component {name!r} category {category!r} contains duplicate resources")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visiting:
            raise ValueError(f"change-impact graph contains a cycle at {name!r}")
        if name in visited:
            return
        visiting.add(name)
        for child in components[name].get("downstream", []):
            visit(child)
        visiting.remove(name)
        visited.add(name)

    for component in components:
        visit(component)


def transitive_components(graph: dict[str, Any], roots: list[str]) -> list[str]:
    validate_impact_graph(graph)
    components = graph["components"]
    unknown = sorted(set(roots) - set(components))
    if unknown:
        raise ValueError(f"unknown changed components {unknown}")
    seen: set[str] = set()
    stack = list(reversed(roots))
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(reversed(components[current].get("downstream", [])))
    return sorted(seen)


def required_impacts(graph: dict[str, Any], roots: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    reached = transitive_components(graph, roots)
    impacts: dict[str, set[str]] = {category: set() for category in IMPACT_CATEGORIES}
    for component in reached:
        for category, resources in graph["components"][component].get("impacts", {}).items():
            impacts[category].update(resources)
    return reached, {category: sorted(values) for category, values in impacts.items()}


def assess_change(graph: dict[str, Any], change: dict[str, Any]) -> dict[str, Any]:
    change_id = str(change.get("change_id", "")).strip()
    if not change_id:
        raise ValueError("every change requires change_id")
    if not str(change.get("rationale", "")).strip():
        raise ValueError(f"change {change_id} requires a non-empty rationale")
    roots = change.get("changed_components", [])
    if not isinstance(roots, list) or not roots:
        raise ValueError(f"change {change_id} requires changed_components")

    reached, required = required_impacts(graph, roots)
    declared_raw = change.get("declared_impacts", {})
    if not isinstance(declared_raw, dict):
        raise ValueError(f"change {change_id} declared_impacts must be an object")
    unknown_categories = sorted(set(declared_raw) - set(IMPACT_CATEGORIES))
    if unknown_categories:
        raise ValueError(f"change {change_id} uses unknown declared categories {unknown_categories}")

    declared: dict[str, list[str]] = {}
    missing: dict[str, list[str]] = {}
    extra: dict[str, list[str]] = {}
    for category in IMPACT_CATEGORIES:
        values = declared_raw.get(category, [])
        if not isinstance(values, list) or any(not isinstance(x, str) or not x for x in values):
            raise ValueError(f"change {change_id} category {category} must be a list of non-empty strings")
        if len(values) != len(set(values)):
            raise ValueError(f"change {change_id} category {category} contains duplicate resources")
        declared[category] = sorted(values)
        missing[category] = sorted(set(required[category]) - set(values))
        extra[category] = sorted(set(values) - set(required[category]))

    return {
        "change_id": change_id,
        "title": str(change.get("title", "")),
        "changed_components": sorted(roots),
        "propagated_components": reached,
        "required": required,
        "declared": declared,
        "missing": missing,
        "extra": extra,
        "passed": not any(missing.values()),
    }


def assess_change_requests(graph: dict[str, Any], requests: dict[str, Any]) -> list[dict[str, Any]]:
    validate_impact_graph(graph)
    changes = requests.get("changes")
    if not isinstance(changes, list) or not changes:
        raise ValueError("change request specification must contain non-empty changes")
    ids = [str(change.get("change_id", "")).strip() for change in changes]
    if len(ids) != len(set(ids)):
        raise ValueError("change_id values must be unique")
    return [assess_change(graph, change) for change in changes]


def _load_traceability(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    mapping: dict[str, str] = {}
    for row in rows:
        tlf_id = str(row.get("tlf_id", "")).strip()
        output_file = str(row.get("output_file", "")).strip()
        if tlf_id:
            if tlf_id in mapping:
                raise ValueError(f"duplicate traceability TLF id {tlf_id}")
            mapping[tlf_id] = output_file
    return mapping


def _resolve_resource(root: Path, category: str, resource: str, tlf_outputs: dict[str, str]) -> tuple[str, bool]:
    if category == "tlfs":
        path = tlf_outputs.get(resource, "")
        if not path:
            return "<unmapped TLF>", False
        return path, (root / path).exists()
    return resource, (root / resource).exists()


def run_change_impact_assessment(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    graph_path = root / "spec" / "change_impact_graph.json"
    requests_path = root / "spec" / "change_requests.json"
    traceability_path = root / "spec" / "analysis_traceability.csv"
    graph = load_json(graph_path)
    requests = load_json(requests_path)
    assessments = assess_change_requests(graph, requests)
    tlf_outputs = _load_traceability(traceability_path)

    rows: list[dict[str, Any]] = []
    unresolved_required = 0
    missing_declared = 0
    extra_declared = 0
    required_relationships = 0

    for assessment in assessments:
        for category in IMPACT_CATEGORIES:
            resources = sorted(set(assessment["required"][category]) | set(assessment["declared"][category]))
            for resource in resources:
                required = resource in assessment["required"][category]
                declared = resource in assessment["declared"][category]
                resolved_path, exists = _resolve_resource(root, category, resource, tlf_outputs)
                if required:
                    required_relationships += 1
                    if not declared:
                        missing_declared += 1
                    if not exists:
                        unresolved_required += 1
                elif declared:
                    extra_declared += 1
                if required and not declared:
                    status = "missing_required"
                elif declared and not required:
                    status = "extra_declared"
                else:
                    status = "matched"
                rows.append(
                    {
                        "change_id": assessment["change_id"],
                        "title": assessment["title"],
                        "category": category,
                        "resource": resource,
                        "resolved_path": resolved_path,
                        "required_by_graph": required,
                        "declared_for_review": declared,
                        "resource_exists": exists,
                        "status": status,
                    }
                )

    all_passed = missing_declared == 0 and unresolved_required == 0 and all(a["passed"] for a in assessments)
    metrics = {
        "analysis_version": "0.10.0",
        "changes_assessed": len(assessments),
        "changed_components": sum(len(a["changed_components"]) for a in assessments),
        "propagated_component_links": sum(len(a["propagated_components"]) for a in assessments),
        "required_impact_relationships": required_relationships,
        "missing_required_declarations": missing_declared,
        "extra_declared_resources": extra_declared,
        "unresolved_required_resources": unresolved_required,
        "all_passed": all_passed,
        "spec_sha256": {
            "change_impact_graph.json": sha256_file(graph_path),
            "change_requests.json": sha256_file(requests_path),
            "analysis_traceability.csv": sha256_file(traceability_path),
        },
        "changes": [
            {
                "change_id": a["change_id"],
                "changed_components": a["changed_components"],
                "propagated_components": a["propagated_components"],
                "required_impacts": sum(len(a["required"][c]) for c in IMPACT_CATEGORIES),
                "missing_required": sum(len(a["missing"][c]) for c in IMPACT_CATEGORIES),
                "extra_declared": sum(len(a["extra"][c]) for c in IMPACT_CATEGORIES),
                "impacted_tlfs": a["required"]["tlfs"],
            }
            for a in assessments
        ],
    }

    lines = [
        "# Statistical change-control impact assessment",
        "",
        "Portfolio simulation only; not a sponsor-approved protocol/SAP change-control record.",
        "",
        f"Required impact declarations: **{required_relationships - missing_declared}/{required_relationships} covered**",
        f"Required resources resolved: **{required_relationships - unresolved_required}/{required_relationships}**",
        f"Overall gate: **{'PASS' if all_passed else 'FAIL'}**",
        "",
        "| Change | Propagated components | Required impacts | Missing | Extra | Impacted TLFs |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for item in metrics["changes"]:
        lines.append(
            f"| {item['change_id']} | {len(item['propagated_components'])} | {item['required_impacts']} | "
            f"{item['missing_required']} | {item['extra_declared']} | {', '.join(item['impacted_tlfs']) or '-'} |"
        )
    lines.extend(
        [
            "",
            "The gate derives required impacts from the dependency graph; the change request must declare every required downstream review item. Conservative extra declarations are reported but do not fail the gate.",
        ]
    )
    return rows, metrics, "\n".join(lines) + "\n"
