from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

VERSION = "0.19.0"
CORE_ID_RE = re.compile(r"\bCORE-\d{6}\b")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def audit_core_cache(
    root: Path,
    cache_dir: Path,
    list_rules_path: Path,
) -> dict[str, Any]:
    root = Path(root)
    cache_dir = Path(cache_dir)
    list_rules_path = Path(list_rules_path)
    cfg = json.loads((root / "spec" / "standards_validation_v0_19.json").read_text(encoding="utf-8"))
    if cfg.get("version") != VERSION:
        raise ValueError("standards-validation config must be version 0.19.0")
    core_cfg = cfg["core"]
    if core_cfg.get("conformance_claim") != "NOT_ASSESSED":
        raise ValueError("CORE conformance claim must remain NOT_ASSESSED")
    if not core_cfg.get("cache_commit_is_engine_ancestor"):
        raise ValueError("pinned CORE cache snapshot must be declared as an ancestor of the pinned engine commit")
    if not cache_dir.is_dir():
        raise ValueError(f"CORE cache directory not found: {cache_dir}")
    if not list_rules_path.is_file():
        raise ValueError(f"CORE list-rules output not found: {list_rules_path}")

    required = list(core_cfg.get("required_cache_files", []))
    if not required:
        raise ValueError("required_cache_files must not be empty")
    files = []
    missing = []
    placeholder = []
    for name in required:
        path = cache_dir / name
        if not path.is_file():
            missing.append(name)
            continue
        size = path.stat().st_size
        if size <= 5:
            placeholder.append(name)
        files.append({"file": name, "bytes": size, "sha256": _sha256(path)})

    list_rules_text = list_rules_path.read_text(encoding="utf-8", errors="replace")
    rule_ids = sorted(set(CORE_ID_RE.findall(list_rules_text)))
    minimum = int(core_cfg.get("minimum_rule_ids", 1))
    checks = [
        {
            "check": "required official CORE cache files exist",
            "passed": not missing,
            "detail": f"missing={missing}",
        },
        {
            "check": "required official CORE cache files are not 5-byte placeholders",
            "passed": not placeholder,
            "detail": f"placeholder={placeholder}",
        },
        {
            "check": "pinned ADaMIG rule set is non-empty",
            "passed": len(rule_ids) >= minimum,
            "detail": f"unique_rule_ids={len(rule_ids)}; minimum={minimum}",
        },
        {
            "check": "formal conformance claim remains disabled",
            "passed": core_cfg.get("conformance_claim") == "NOT_ASSESSED",
            "detail": "portfolio validation evidence only",
        },
    ]
    all_passed = all(row["passed"] for row in checks)
    return {
        "analysis_version": VERSION,
        "core_repository": core_cfg.get("repository"),
        "core_commit": core_cfg.get("commit"),
        "cache_repository": core_cfg.get("cache_repository"),
        "cache_commit": core_cfg.get("cache_commit"),
        "cache_commit_is_engine_ancestor": bool(core_cfg.get("cache_commit_is_engine_ancestor")),
        "standard": core_cfg.get("standard"),
        "version": core_cfg.get("version"),
        "required_cache_files": files,
        "missing_cache_files": missing,
        "placeholder_cache_files": placeholder,
        "rule_ids": rule_ids,
        "rule_count": len(rule_ids),
        "list_rules_sha256": _sha256(list_rules_path),
        "checks": checks,
        "conformance_claim": "NOT_ASSESSED",
        "all_passed": all_passed,
    }


def write_core_cache_outputs(root: Path, cache_dir: Path, list_rules_path: Path) -> dict[str, Any]:
    root = Path(root)
    metrics = audit_core_cache(root, cache_dir, list_rules_path)
    outputs = root / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    (outputs / "core_cache_manifest.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# Pinned CDISC CORE cache audit",
        "",
        f"- Engine commit: `{metrics['core_commit']}`.",
        f"- Official cache commit: `{metrics['cache_commit']}`.",
        f"- Requested ruleset: `{metrics['standard']} {metrics['version']}`.",
        f"- Unique CORE rule IDs returned by `list-rules`: {metrics['rule_count']}.",
        f"- Required cache files missing: {len(metrics['missing_cache_files'])}.",
        f"- Required cache placeholder files: {len(metrics['placeholder_cache_files'])}.",
        f"- Cache gate: {'PASS' if metrics['all_passed'] else 'FAIL'}.",
        "",
        "The rule cache is copied from a pinned official CDISC repository commit that is an ancestor of the pinned engine commit. No live update-cache result is used as the validation baseline.",
        "This provenance check supports reproducibility; it is not a formal ADaM conformance claim.",
    ]
    (outputs / "core_cache_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if not metrics["all_passed"]:
        raise ValueError("pinned CDISC CORE cache gate failed; inspect outputs/core_cache_manifest.json")
    return metrics
