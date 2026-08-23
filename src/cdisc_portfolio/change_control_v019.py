from __future__ import annotations

from pathlib import Path
from typing import Any

from .change_control import (
    IMPACT_CATEGORIES,
    _load_traceability,
    _resolve_resource,
    assess_change_requests,
    load_json,
    sha256_file,
)
from .change_control_v015 import merge_graph_extension, merge_request_extension
from .change_control_v018 import load_versioned_change_control as load_v018_change_control

GRAPH_EXTENSION = "change_impact_graph_v0_19_extension.json"
REQUEST_EXTENSION = "change_requests_v0_19_extension.json"


def _require_v019_versions(
    prior_version: str,
    graph_extension: dict[str, Any],
    request_extension: dict[str, Any],
) -> str:
    graph_base = str(graph_extension.get("base_version", "")).strip()
    request_base = str(request_extension.get("base_version", "")).strip()
    if graph_base != prior_version or request_base != prior_version:
        raise ValueError(
            "v0.19 extensions must declare the exact merged v0.18 base version "
            f"{prior_version}; graph extension={graph_base}; request extension={request_base}"
        )
    graph_version = str(graph_extension.get("version", "")).strip()
    request_version = str(request_extension.get("version", "")).strip()
    if not graph_version or graph_version != request_version:
        raise ValueError(
            f"v0.19 extension version mismatch: graph={graph_version}; requests={request_version}"
        )
    if graph_version == prior_version:
        raise ValueError("v0.19 extension must advance beyond the merged v0.18 version")
    return graph_version


def load_versioned_change_control(
    root: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path], str]:
    prior_graph, prior_requests, prior_paths, prior_version = load_v018_change_control(root)
    spec_dir = root / "spec"
    graph_path = spec_dir / GRAPH_EXTENSION
    request_path = spec_dir / REQUEST_EXTENSION
    graph_extension = load_json(graph_path)
    request_extension = load_json(request_path)
    version = _require_v019_versions(prior_version, graph_extension, request_extension)
    graph = merge_graph_extension(prior_graph, graph_extension)
    requests = merge_request_extension(prior_requests, request_extension)
    if graph.get("version") != version or requests.get("version") != version:
        raise ValueError("merged change-control version did not resolve to v0.19 extension version")
    paths = dict(prior_paths)
    paths["graph_extension_v019"] = graph_path
    paths["request_extension_v019"] = request_path
    return graph, requests, paths, version


def run_change_impact_assessment(
    root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    graph, requests, paths, version = load_versioned_change_control(root)
    assessments = assess_change_requests(graph, requests)
    tlf_outputs = _load_traceability(paths["traceability"])
    rows: list[dict[str, Any]] = []
    unresolved_required = missing_declared = extra_declared = required_relationships = 0

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
                status = (
                    "missing_required"
                    if required and not declared
                    else "extra_declared"
                    if declared and not required
                    else "matched"
                )
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
    base_graph_version = str(load_json(paths["base_graph"]).get("version", ""))
    metrics = {
        "analysis_version": version,
        "base_change_control_version": base_graph_version,
        "prior_extension_version": "0.18.0",
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
                    len(a["required"][category]) for category in IMPACT_CATEGORIES
                ),
                "missing_required": sum(
                    len(a["missing"][category]) for category in IMPACT_CATEGORIES
                ),
                "extra_declared": sum(
                    len(a["extra"][category]) for category in IMPACT_CATEGORIES
                ),
                "impacted_tlfs": a["required"]["tlfs"],
            }
            for a in assessments
        ],
    }

    lines = [
        "# Statistical change-control impact assessment",
        "",
        f"Change-control specification version: **{version}** (byte-preserved base {base_graph_version} + v0.15 + v0.16 + v0.17 + v0.18 + v0.19 controlled extensions)",
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
            "v0.19 adds official Dataset-JSON exchange/schema validation plus pinned CDISC CORE cache/rule-availability evidence over the validated v0.18 metadata layer.",
            "",
            "CR-013 intentionally has no impacted TLFs and does not alter MMRM, multiplicity, missing-data sensitivity or retention-survival families. A zero-rule ADaMIG CORE cache is recorded as NOT_AVAILABLE_IN_PINNED_OFFICIAL_CACHE, never as zero issues or formal conformance.",
        ]
    )
    return rows, metrics, "\n".join(lines) + "\n"
