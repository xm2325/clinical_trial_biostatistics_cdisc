from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RandomisationResult:
    unblinded: pd.DataFrame
    blinded: pd.DataFrame
    kit_code_list: pd.DataFrame
    balance: pd.DataFrame
    block_summary: pd.DataFrame
    qc: pd.DataFrame


def _require_positive_int(value: Any, name: str) -> int:
    out = int(value)
    if out < 1 or float(value) != out:
        raise ValueError(f"{name} must be a positive integer")
    return out


def _format_id(prefix: str, value: int, width: int) -> str:
    return f"{prefix}{value:0{width}d}"


def _longest_run(values: list[str]) -> int:
    if not values:
        return 0
    longest = current = 1
    for previous, current_value in zip(values, values[1:]):
        if current_value == previous:
            current += 1
        else:
            current = 1
        longest = max(longest, current)
    return longest


def generate_randomisation_schedule(spec: dict[str, Any]) -> RandomisationResult:
    """Generate a reproducible equal-allocation stratified permuted-block schedule.

    The implementation is intentionally limited to equal allocation because that
    is the design specified by this portfolio. Production randomisation systems
    require additional controls, access management and operational validation.
    """
    allocation = spec["allocation"]
    arm_specs = list(allocation["arms"])
    if len(arm_specs) < 2:
        raise ValueError("at least two treatment arms are required")

    treatments = [str(x["treatment"]) for x in arm_specs]
    blind_codes = [str(x["blind_code"]) for x in arm_specs]
    if len(set(treatments)) != len(treatments):
        raise ValueError("treatment labels must be unique")
    if len(set(blind_codes)) != len(blind_codes):
        raise ValueError("blind codes must be unique")

    ratios = [int(x) for x in allocation["ratio"]]
    if len(ratios) != len(treatments) or any(x != 1 for x in ratios):
        raise ValueError("this portfolio generator supports equal 1:1:... allocation only")

    n_arms = len(treatments)
    allowed_blocks = sorted({_require_positive_int(x, "block size") for x in allocation["allowed_block_sizes"]})
    if any(block % n_arms != 0 for block in allowed_blocks):
        raise ValueError("every allowed block size must be divisible by the number of arms")

    strata = list(spec["strata"])
    if not strata:
        raise ValueError("at least one stratum is required")
    stratum_names = [str(x["stratum"]) for x in strata]
    if len(set(stratum_names)) != len(stratum_names):
        raise ValueError("stratum names must be unique")

    planned_by_stratum: dict[str, int] = {}
    for item in strata:
        name = str(item["stratum"])
        planned_n = _require_positive_int(item["planned_n"], f"planned_n for {name}")
        if planned_n % n_arms != 0:
            raise ValueError(f"planned_n for {name} must be divisible by the number of arms")
        planned_by_stratum[name] = planned_n

    planned_total = sum(planned_by_stratum.values())
    design_total = _require_positive_int(spec["design_link"]["planned_total_randomised"], "planned_total_randomised")
    if planned_total != design_total:
        raise ValueError(f"stratum totals ({planned_total}) do not match planned_total_randomised ({design_total})")

    seed = int(spec["random_seed"])
    rng = np.random.default_rng(seed)
    treatment_to_code = dict(zip(treatments, blind_codes))

    ids = spec["identifiers"]
    rand_prefix = str(ids["randomisation_prefix"])
    rand_width = _require_positive_int(ids["randomisation_width"], "randomisation_width")
    kit_prefix = str(ids["kit_prefix"])
    kit_width = _require_positive_int(ids["kit_width"], "kit_width")
    kit_start = _require_positive_int(ids["kit_start"], "kit_start")

    rows: list[dict[str, Any]] = []
    rand_counter = 1
    for stratum in stratum_names:
        remaining = planned_by_stratum[stratum]
        block_number = 1
        while remaining > 0:
            candidates = [b for b in allowed_blocks if b <= remaining]
            if not candidates:
                raise ValueError(f"no allowed block size can complete {stratum}; remaining={remaining}")
            block_size = int(rng.choice(candidates))
            repeats = block_size // n_arms
            assignments = np.repeat(np.array(treatments, dtype=object), repeats)
            assignments = rng.permutation(assignments).tolist()
            block_id = f"{stratum}-B{block_number:03d}"
            for position, treatment in enumerate(assignments, start=1):
                rows.append(
                    {
                        "randomisation_id": _format_id(rand_prefix, rand_counter, rand_width),
                        "stratum": stratum,
                        "block_id": block_id,
                        "block_size": block_size,
                        "position_in_block": position,
                        "treatment": treatment,
                        "blind_code": treatment_to_code[treatment],
                    }
                )
                rand_counter += 1
            remaining -= block_size
            block_number += 1

    unblinded = pd.DataFrame(rows)

    # Create a separate coded kit pool, balanced to the generated treatment counts.
    kit_rows: list[dict[str, str]] = []
    next_kit = kit_start
    for treatment in treatments:
        count = int(unblinded["treatment"].eq(treatment).sum())
        for _ in range(count):
            kit_rows.append(
                {
                    "kit_id": _format_id(kit_prefix, next_kit, kit_width),
                    "treatment": treatment,
                    "blind_code": treatment_to_code[treatment],
                }
            )
            next_kit += 1
    kit_code_list = pd.DataFrame(kit_rows)
    kit_code_list = kit_code_list.iloc[rng.permutation(len(kit_code_list))].reset_index(drop=True)

    kit_pool: dict[str, list[str]] = {}
    for treatment in treatments:
        pool = kit_code_list.loc[kit_code_list["treatment"].eq(treatment), "kit_id"].tolist()
        kit_pool[treatment] = list(rng.permutation(np.array(pool, dtype=object)))

    assigned_kits: list[str] = []
    treatment_cursor = {t: 0 for t in treatments}
    for treatment in unblinded["treatment"]:
        cursor = treatment_cursor[treatment]
        assigned_kits.append(kit_pool[treatment][cursor])
        treatment_cursor[treatment] += 1
    unblinded["kit_id"] = assigned_kits

    blinded = unblinded[["randomisation_id", "stratum", "kit_id"]].copy()

    overall = (
        unblinded.groupby("treatment", as_index=False)
        .size()
        .rename(columns={"size": "n"})
        .assign(stratum="OVERALL")
    )
    by_stratum = (
        unblinded.groupby(["stratum", "treatment"], as_index=False)
        .size()
        .rename(columns={"size": "n"})
    )
    balance = pd.concat([overall[["stratum", "treatment", "n"]], by_stratum], ignore_index=True)

    block_summary = (
        unblinded.groupby(["stratum", "block_id", "block_size", "treatment"], as_index=False)
        .size()
        .rename(columns={"size": "n"})
    )

    qc_rows: list[dict[str, Any]] = []

    def add_check(check: str, passed: bool, detail: str, required: bool = True) -> None:
        qc_rows.append({"check": check, "passed": bool(passed), "required": required, "detail": detail})

    add_check(
        "Generated randomisation count matches planned total",
        len(unblinded) == planned_total,
        f"generated={len(unblinded)}; planned={planned_total}",
    )
    add_check(
        "Randomisation identifiers are unique",
        unblinded["randomisation_id"].is_unique,
        f"unique={unblinded['randomisation_id'].nunique()}; rows={len(unblinded)}",
    )
    add_check(
        "Kit identifiers are unique",
        unblinded["kit_id"].is_unique and kit_code_list["kit_id"].is_unique,
        f"assigned unique={unblinded['kit_id'].nunique()}; code-list unique={kit_code_list['kit_id'].nunique()}",
    )

    overall_counts = unblinded.groupby("treatment").size().reindex(treatments)
    add_check(
        "Overall treatment allocation is exactly balanced",
        overall_counts.nunique() == 1,
        ", ".join(f"{t}={int(overall_counts[t])}" for t in treatments),
    )

    stratum_balanced = True
    stratum_details: list[str] = []
    for stratum in stratum_names:
        counts = unblinded.loc[unblinded["stratum"].eq(stratum)].groupby("treatment").size().reindex(treatments, fill_value=0)
        expected = planned_by_stratum[stratum] // n_arms
        passed = bool((counts == expected).all())
        stratum_balanced &= passed
        stratum_details.append(f"{stratum}: {counts.to_dict()}")
    add_check(
        "Treatment allocation is balanced within every stratum",
        stratum_balanced,
        "; ".join(stratum_details),
    )

    block_balanced = True
    bad_blocks: list[str] = []
    for block_id, g in unblinded.groupby("block_id", sort=False):
        counts = g.groupby("treatment").size().reindex(treatments, fill_value=0)
        if counts.nunique() != 1:
            block_balanced = False
            bad_blocks.append(str(block_id))
    add_check(
        "Every permuted block is balanced across treatment arms",
        block_balanced,
        f"blocks={unblinded['block_id'].nunique()}; unbalanced={bad_blocks}",
    )

    mapping = kit_code_list.set_index("kit_id")["treatment"]
    mapped_treatment = unblinded["kit_id"].map(mapping)
    add_check(
        "Assigned kit treatment matches unblinded randomisation treatment",
        bool(mapped_treatment.eq(unblinded["treatment"]).all()),
        f"mismatches={int((mapped_treatment != unblinded['treatment']).sum())}",
    )

    add_check(
        "Blinded schedule contains no treatment allocation columns",
        not bool({"treatment", "blind_code", "block_id", "block_size", "position_in_block"}.intersection(blinded.columns)),
        f"columns={list(blinded.columns)}",
    )
    add_check(
        "Blinded and unblinded schedule keys reconcile",
        set(zip(blinded["randomisation_id"], blinded["kit_id"]))
        == set(zip(unblinded["randomisation_id"], unblinded["kit_id"])),
        f"blinded rows={len(blinded)}; unblinded rows={len(unblinded)}",
    )
    add_check(
        "Kit code list covers every assigned kit exactly once",
        set(kit_code_list["kit_id"]) == set(unblinded["kit_id"]) and len(kit_code_list) == len(unblinded),
        f"kit-code rows={len(kit_code_list)}; assignments={len(unblinded)}",
    )

    run_details = []
    for stratum in stratum_names:
        sequence = unblinded.loc[unblinded["stratum"].eq(stratum), "treatment"].tolist()
        run_details.append(f"{stratum}={_longest_run(sequence)}")
    add_check(
        "Longest same-treatment run is reported",
        True,
        "; ".join(run_details),
        required=False,
    )

    qc = pd.DataFrame(qc_rows)
    return RandomisationResult(
        unblinded=unblinded,
        blinded=blinded,
        kit_code_list=kit_code_list,
        balance=balance,
        block_summary=block_summary,
        qc=qc,
    )
