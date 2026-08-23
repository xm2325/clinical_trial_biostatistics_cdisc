import json
from pathlib import Path

import pytest

from cdisc_portfolio.core_cache import audit_core_cache, write_core_cache_outputs


def _cfg() -> dict:
    return {
        "version": "0.19.0",
        "core": {
            "repository": "cdisc-org/cdisc-rules-engine",
            "commit": "engine-commit",
            "cache_repository": "cdisc-org/cdisc-rules-engine",
            "cache_commit": "cache-commit",
            "cache_commit_is_engine_ancestor": True,
            "standard": "adamig",
            "version": "1-3",
            "required_cache_files": [
                "rules.pkl",
                "standards_details.pkl",
                "standards_models.pkl",
                "variables_metadata.pkl",
            ],
            "minimum_rule_ids": 1,
            "conformance_claim": "NOT_ASSESSED",
        },
    }


def _write_fixture(tmp_path: Path, rule_text: str = "CORE-000123\nCORE-000456\n") -> tuple[Path, Path]:
    (tmp_path / "spec").mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "spec" / "standards_validation_v0_19.json").write_text(
        json.dumps(_cfg()), encoding="utf-8"
    )
    cache = tmp_path / "cache"
    cache.mkdir()
    for name in _cfg()["core"]["required_cache_files"]:
        (cache / name).write_bytes((name * 2).encode("utf-8"))
    rules = tmp_path / "list_rules.txt"
    rules.write_text(rule_text, encoding="utf-8")
    return cache, rules


def test_cache_audit_records_rule_ids_hashes_and_pins(tmp_path: Path) -> None:
    cache, rules = _write_fixture(tmp_path)
    metrics = audit_core_cache(tmp_path, cache, rules)
    assert metrics["all_passed"] is True
    assert metrics["rule_ids"] == ["CORE-000123", "CORE-000456"]
    assert metrics["rule_count"] == 2
    assert metrics["cache_commit"] == "cache-commit"
    assert metrics["cache_commit_is_engine_ancestor"] is True
    assert len(metrics["list_rules_sha256"]) == 64
    assert all(len(row["sha256"]) == 64 for row in metrics["required_cache_files"])


def test_five_byte_placeholder_cache_is_blocking(tmp_path: Path) -> None:
    cache, rules = _write_fixture(tmp_path)
    (cache / "rules.pkl").write_bytes(b"abcde")
    metrics = audit_core_cache(tmp_path, cache, rules)
    assert metrics["all_passed"] is False
    assert metrics["placeholder_cache_files"] == ["rules.pkl"]


def test_zero_rule_ids_is_blocking(tmp_path: Path) -> None:
    cache, rules = _write_fixture(tmp_path, rule_text="No rules found\n")
    metrics = audit_core_cache(tmp_path, cache, rules)
    assert metrics["all_passed"] is False
    assert metrics["rule_count"] == 0


def test_non_ancestor_cache_declaration_is_rejected(tmp_path: Path) -> None:
    cache, rules = _write_fixture(tmp_path)
    cfg = _cfg()
    cfg["core"]["cache_commit_is_engine_ancestor"] = False
    (tmp_path / "spec" / "standards_validation_v0_19.json").write_text(
        json.dumps(cfg), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="ancestor"):
        audit_core_cache(tmp_path, cache, rules)


def test_conformance_overclaim_is_rejected(tmp_path: Path) -> None:
    cache, rules = _write_fixture(tmp_path)
    cfg = _cfg()
    cfg["core"]["conformance_claim"] = "CONFORMANT"
    (tmp_path / "spec" / "standards_validation_v0_19.json").write_text(
        json.dumps(cfg), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="NOT_ASSESSED"):
        audit_core_cache(tmp_path, cache, rules)


def test_write_cache_outputs_emits_manifest_and_summary(tmp_path: Path) -> None:
    cache, rules = _write_fixture(tmp_path)
    metrics = write_core_cache_outputs(tmp_path, cache, rules)
    assert metrics["all_passed"] is True
    assert (tmp_path / "outputs" / "core_cache_manifest.json").is_file()
    assert (tmp_path / "outputs" / "core_cache_summary.md").is_file()
