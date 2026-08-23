from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.core_cache import write_core_cache_outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit pinned official CDISC CORE cache provenance and rule availability")
    parser.add_argument("--cache-dir", required=True, type=Path)
    parser.add_argument("--list-rules", required=True, type=Path)
    parser.add_argument("--list-all-rules", type=Path)
    parser.add_argument("--open-rules-root", type=Path)
    args = parser.parse_args()
    metrics = write_core_cache_outputs(
        ROOT,
        args.cache_dir,
        args.list_rules,
        open_rules_root=args.open_rules_root,
        list_all_rules_path=args.list_all_rules,
    )
    print(
        "CORE cache audit: "
        f"cache_commit={metrics['cache_commit']}; requested_rules={metrics['rule_count']}; "
        f"all_rules={metrics['all_rule_count']}; state={metrics['ruleset_state']}; "
        f"unpublished_adamig={metrics['unpublished_adamig_rule_count']}; "
        f"missing={len(metrics['missing_cache_files'])}; "
        f"placeholders={len(metrics['placeholder_cache_files'])}; "
        f"passed={metrics['all_passed']}"
    )


if __name__ == "__main__":
    main()
