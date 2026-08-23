from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .change_control import (
    IMPACT_CATEGORIES,
    _load_traceability,
    _resolve_resource,
    assess_change_requests,
    load_json,
    sha256_file,
    validate_impact_graph,
)


GRAPH_BASE = "change_impact_graph.json"
REQUEST_BASE = "change_requests.json"
GRAPH_EXTENSION = "change_impact_graph_v0_15_extension.json"
REQUEST_EXTENSION = "change_requests_v0_15_extension.json"


def _require_extension_versions(
    base_graph: dict[str, Any],
    base_requests: dict[str, Any],
    graph_extension: dict[str, Any],
    request_extension: dict[str, Any],
) -> str:
    graph_base_version = str(base_graph.get("version", "")).strip()
    request_base_version = str(base_requests.get("version", "")).strip()
    if not graph_base_version or graph_base_version != request_base_version:
        raise ValueError(
            f"base change-control version mismatch: graph={graph_base_version}; requests={request_base_version}"
        )

    graph_expected_base = str(graph_extension.get("base_version", "")).strip()
    request_expected_base = str(request_extension.get("base_version", "")).strip()
    if graph_expected_base != graph_base_version or request_expected_base != graph_base_version:
        raise ValueError(
            "v0.15 extensions must declare the exact base change-control version "
            f"{graph_base_version}; graph extension={graph_expected_base}; request extension={request_expected_base}"
        )

    graph_version = str(graph_extension.get("version", "")).strip()
    request_version = str(request_extension.get("version", "")).strip()
    if not graph_version or graph_version != request_version:
        raise ValueError(
            f"extension version mismatch: graph={graph_version}; requests={request_version}"
        )
    if graph_version == graph_base_version:
        raise ValueError("extension version must advance beyond the base version")
    return graph_version


def merge_graph_extension(
    base_graph: dict[str, Any],
    extension: dict[str, Any],
) -> dict[str, Any]:
    merged = deepcopy(base_graph)
    base_version = str(base_graph.get("version", "")).strip()
    if str(extension.get("base_version", "")).strip() != base_version:
        raise ValueError("graph extension base_version does not match base graph")

    new_version = str(extension.get("version", "")).strip()
    if not new_version:
        raise ValueError("graph extension requires version")

    components = merged.get("components")
    if not isinstance(components, dict):
        raise ValueError("base graph components must be an object")

    additions = extension.get("components", {})
    if not isinstance(additions, dict) or not additions:
        raise ValueError("graph extension requires non-empty component additions")
    overlap = sorted(set(additions) & set(components))
    if overlap:
        raise ValueError(f"graph extension component collisions: {overlap}")
    for name, node in additions.items():
        components[name] = deepcopy(node)

    downstream_additions = extension.get("downstream_additions", {})
    if not isinstance(downstream_additions, dict):
        raise ValueError("downstream_additions must be an object")
    for parent, children in downstream_additions.items():
        if parent not in components:
            raise ValueError(f"downstream addition references unknown parent {parent!r}")
        if not isinstance(children, list) or any(not isinstance(x, str) or not x for x in children):
            raise ValueError(f"downstream additions for {parent!r} must be non-empty strings")
        unknown = sorted(set(children) - set(components))
        if unknown:
            raise ValueError(f"downstream addition for {parent!r} references unknown children {unknown}")
        current = list(components[parent].get("downstream", []))
        for child in children:
            if child not in current:
                current.append(child)
        components[parent]["downstream"] = current

    merged["version"] = new_version
    validate_impact_graph(merged)
    return merged


def merge_request_extension(
    base_requests: dict[str, Any],
    extension: dict[str, Any],
) -> dict[str, Any]:
    merged = deepcopy(base_requests)
    base_version = str(base_requests.get("version", "")).strip()
    if str(extension.get("base_version", "")).strip() != base_version:
        raise ValueError("request extension base_version does not match base requests")

    new_version = str(extension.get("version", "")).strip()
    if not new_version:
        raise ValueError("request extension requires version")

    changes = merged.get("changes")
    if not isinstance(changes, list) or not changes:
        raise ValueError("base change requests must contain changes")
    by_id = {str(change.get("change_id", "")).strip(): change for change in changes}

    declared_additions = extension.get("declared_impact_additions", {})
    if not isinstance(declared_additions, dict):
        raise ValueError("declared_impact_additions must be an object")
    for change_id, category_map in declared_additions.items():
        if change_id not in by_id:
            raise ValueError(f"declared impact addition references unknown change {change_id}")
        if not isinstance(category_map, dict):
            raise ValueError(f"declared impact additions for {change_id} must be an object")
        unknown_categories = sorted(set(category_map) - set(IMPACT_CATEGORIES))
        if unknown_categories:
            raise ValueError(f"{change_id} extension uses unknown impact categories {unknown_categories}")
        declared = by_id[change_id].setdefault("declared_impacts", {})
        for category, resources in category_map.items():
            if not isinstance(resources, list) or any(not isinstance(x, str) or not x for x in resources):
                raise ValueError(f"{change_id} {category} additions must be non-empty strings")
            current = list(declared.get(category, []))
            for resource in resources:
                if resource not in current:
                    current.append(resource)
            declared[category] = current

    new_changes = extension.get("changes", [])
    if not isinstance(new_changes, list) or not new_changes:
        raise ValueError("request extension requires at least one new change")
    existing_ids = set(by_id)
    new_ids = [str(change.get("change_id", "")).strip() for change in new_changes]
    if any(not change_id for change_id in new_ids):
        raise ValueError("extension changes require change_id")
    collisions = sorted(existing_ids & set(new_ids))
    if collisions:
        raise ValueError(f"request extension change_id collisions: {collisions}")
    if len(new_ids) != len(set(new_ids)):
        raise ValueError("request extension change_id values must be unique")
    changes.extend(deepcopy(new_changes))

    merged["version"] = new_version
    return merged


def load_versioned_change_control(
    root: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path], str]:
    spec_dir = root / "spec"
    paths = {
        "base_graph": spec_dir / GRAPH_BASE,
        "base_requests": spec_dir / REQUEST_BASE,
        "graph_extension": spec_dir / GRAPH_EXTENSION,
        "request_extension": spec_dir / REQUEST_EXTENSION,
        "traceability": spec_dir / "analysis_traceability.csv",
    }
    base_graph = load_json(paths["base_graph"])
    base_requests = load_json(paths["base_requests"])
    graph_extension = load_json(paths["graph_extension"])
    request_extension = load_json(paths["request_extension"])

    version = _require_extension_versions(
        base_graph, base_requests, graph_extension, request_extension
    )
    graph = merge_graph_extension(base_graph, graph_extension)
    requests = merge_request_extension(base_requests, request_extension)
    if graph.get("version") != version or requests.get("version") != version:
        raise ValueError("merged change-control version did not resolve to extension version")
    return graph, requests, paths, version


def run_change_impact_assessment(
    root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    graph, requests, paths, version = load_versioned_change_control(root)
    assessments = assess_change_requests(graph, requests)
    tlf_outputs = _load_traceability(paths["traceability"])

    rows: list[dict[str, Any]] = []
    unresolved_required = 0
    missing_declared = 0
    extra_declared = 0
    required_relationships = 0

    for assessment in assessments:
        for category in IMPACT_CATEGORIES:
            resources = sorted(
                set(assessment["required"][category])
                | set(assessment["declared"][category])
            )
            for resource in resources:
                required = resource in assessment["required"][category]
                declared = resource in assessment["declared"][category]
                resolved_path, exists = _resolve_resource(
                    root, category, resource, tlf_outputs
                )
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

    all_passed = (
        missing_declared == 0
        and unresolved_required == 0
        and all(a["passed"] for a in assessments)
    )
    metrics = {
        "analysis_version": version,
        "base_change_control_version": str(load_json(paths["base_graph"]).get("version", "")),
        "changes_assessed": len(assessments),
        "changed_components": sum(len(a["changed_components"]) for a in assessments),
        "propagated_component_links": sum(
            len(a["propagated_components"]) for a in assessments
        ),
        "required_impact_relationships": required_relationships,
        "missing_required_declarations": missing_declared,
        "extra_declared_resources": extra_declared,
        "unresolved_required_resources": unresolved_required,
        "all_passed": all_passed,
        "spec_sha256": {
            path.name: sha256_file(path)
            for key, path in paths.items()
            if key != "traceability"
        }
        | {"analysis_traceability.csv": sha256_file(paths["traceability"])},
        "changes": [
            {
                "change_id": a["change_id"],
                "changed_components": a["changed_components"],
                "propagated_components": a["propagated_components"],
                "required_impacts": sum(
                    len(a["required"][c]) for c in IMPACT_CATEGORIES
                ),
                "missing_required": sum(
                    len(a["missing"][c]) for c in IMPACT_CATEGORIES
                ),
                "extra_declared": sum(
                    len(a["extra"][c]) for c in IMPACT_CATEGORIES
                ),
                "impacted_tlfs": a["required"]["tlfs"],
            }
            for a in assessments
        ],
    }

    lines = [
        "# Statistical change-control impact assessment",
        "",
        f"Change-control specification version: **{version}** "
        f"(base {metrics['base_change_control_version']} + controlled v0.15 extension)",
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
            f"| {item['change_id']} | {len(item['propagated_components'])} | "
            f"{item['required_impacts']} | {item['missing_required']} | "
            f"{item['extra_declared']} | {', '.join(item['impacted_tlfs']) or '-'} |"
        )
    lines.extend(
        [
            "",
            "v0.15 is layered on the byte-preserved v0.14 base change-control specifications. "
            "The extension adds multiplicity components, CR-009 and only the downstream "
            "declarations newly required for T23.",
            "",
            "The gate derives required impacts from the merged dependency graph; every required "
            "downstream review item must be declared. Conservative extras are reported but do not fail the gate.",
        ]
    )
    return rows, metrics, "\n".join(lines) + "\n"
