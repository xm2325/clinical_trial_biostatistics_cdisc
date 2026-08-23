from __future__ import annotations

import hashlib
import json
import pickletools
import re
from pathlib import Path
from typing import Any

VERSION = "0.19.0"
CORE_ID_RE = re.compile(r"\bCORE-\d{6}\b")
RULESET_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_-]+)?$")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _pickle_string_tokens(path: Path) -> list[str]:
    """Read literal string opcodes without executing pickle payloads."""
    values: set[str] = set()
    with Path(path).open("rb") as handle:
        for opcode, arg, _ in pickletools.genops(handle):
            if opcode.name in {
                "UNICODE",
                "BINUNICODE",
                "BINUNICODE8",
                "SHORT_BINUNICODE",
                "STRING",
                "BINSTRING",
                "SHORT_BINSTRING",
            }:
                if isinstance(arg, bytes):
                    text = arg.decode("utf-8", errors="replace")
                else:
                    text = str(arg)
                values.add(text)
    return sorted(values)


def _ruleset_keys_from_dictionary(path: Path) -> list[str]:
    return sorted(
        value for value in _pickle_string_tokens(path) if RULESET_KEY_RE.fullmatch(value)
    )


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

    rules_dictionary = cache_dir / "rules_dictionary.pkl"
    ruleset_keys = _ruleset_keys_from_dictionary(rules_dictionary) if rules_dictionary.is_file() else []
    requested_ruleset = f"{core_cfg.get('standard')}/{core_cfg.get('version')}"
    requested_ruleset_present = requested_ruleset in ruleset_keys
    related_rulesets = [
        key for key in ruleset_keys if key.lower().startswith(f"{str(core_cfg.get('standard')).lower()}/")
    ]

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
            "check": "requested ADaMIG rule-set key exists in pinned dictionary",
            "passed": requested_ruleset_present,
            "detail": f"requested={requested_ruleset}; related={related_rulesets}",
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
        "ruleset_keys": ruleset_keys,
        "ruleset_key_count": len(ruleset_keys),
        "requested_ruleset": requested_ruleset,
        "requested_ruleset_present": requested_ruleset_present,
        "related_rulesets": related_rulesets,
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
        f"- Requested ruleset: `{metrics['requested_ruleset']}`.",
        f"- Requested ruleset present in rules dictionary: {metrics['requested_ruleset_present']}.",
        f"- Related rulesets in dictionary: {metrics['related_rulesets']}.",
        f"- Unique CORE rule IDs returned by `list-rules`: {metrics['rule_count']}.",
        f"- Required cache files missing: {len(metrics['missing_cache_files'])}.",
        f"- Required cache placeholder files: {len(metrics['placeholder_cache_files'])}.",
        f"- Cache gate: {'PASS' if metrics['all_passed'] else 'FAIL'}.",
        "",
        "The rule cache is copied from a pinned official CDISC repository commit that is an ancestor of the pinned engine commit. Rule-set keys are inspected with pickletools without executing pickle payloads, and no live update-cache result is used as the validation baseline.",
        "This provenance check supports reproducibility; it is not a formal ADaM conformance claim.",
    ]
    (outputs / "core_cache_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if not metrics["all_passed"]:
        raise ValueError("pinned CDISC CORE cache gate failed; inspect outputs/core_cache_manifest.json")
    return metrics
