import copy
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdisc_portfolio.randomisation import generate_randomisation_schedule


def _spec():
    return json.loads((ROOT / "spec" / "randomisation_schedule.json").read_text())


def test_randomisation_is_deterministic_for_same_seed():
    first = generate_randomisation_schedule(_spec())
    second = generate_randomisation_schedule(_spec())
    pd.testing.assert_frame_equal(first.unblinded, second.unblinded)
    pd.testing.assert_frame_equal(first.kit_code_list, second.kit_code_list)


def test_randomisation_changes_sequence_with_different_seed_but_preserves_balance():
    spec_a = _spec()
    spec_b = copy.deepcopy(spec_a)
    spec_b["random_seed"] += 1
    a = generate_randomisation_schedule(spec_a)
    b = generate_randomisation_schedule(spec_b)
    assert not a.unblinded["treatment"].equals(b.unblinded["treatment"])
    assert a.unblinded.groupby("treatment").size().to_dict() == b.unblinded.groupby("treatment").size().to_dict()


def test_randomisation_matches_linked_total_and_overall_allocation():
    result = generate_randomisation_schedule(_spec())
    assert len(result.unblinded) == 390
    assert result.unblinded.groupby("treatment").size().to_dict() == {
        "Placebo": 130,
        "Xanomeline High Dose": 130,
        "Xanomeline Low Dose": 130,
    }


def test_each_stratum_is_exactly_balanced():
    result = generate_randomisation_schedule(_spec())
    counts = result.unblinded.groupby(["stratum", "treatment"]).size().unstack(fill_value=0)
    assert counts.shape == (5, 3)
    assert (counts == 26).all().all()


def test_every_permuted_block_is_balanced():
    result = generate_randomisation_schedule(_spec())
    for _, block in result.unblinded.groupby("block_id"):
        counts = block.groupby("treatment").size()
        assert counts.nunique() == 1
        assert len(counts) == 3


def test_blinded_schedule_does_not_disclose_allocation_or_block_structure():
    result = generate_randomisation_schedule(_spec())
    assert result.blinded.columns.tolist() == ["randomisation_id", "stratum", "kit_id"]
    assert not {"treatment", "blind_code", "block_id", "block_size", "position_in_block"}.intersection(result.blinded.columns)


def test_kit_mapping_is_unique_and_matches_every_assignment():
    result = generate_randomisation_schedule(_spec())
    assert result.unblinded["kit_id"].is_unique
    assert result.kit_code_list["kit_id"].is_unique
    mapping = result.kit_code_list.set_index("kit_id")["treatment"]
    assert result.unblinded["kit_id"].map(mapping).equals(result.unblinded["treatment"])


def test_required_randomisation_qc_all_passes():
    result = generate_randomisation_schedule(_spec())
    required = result.qc[result.qc["required"]]
    assert len(required) == 10
    assert required["passed"].all()


def test_rejects_stratum_total_not_divisible_by_arm_count():
    spec = _spec()
    spec["strata"][0]["planned_n"] = 79
    spec["design_link"]["planned_total_randomised"] = 391
    with pytest.raises(ValueError, match="must be divisible"):
        generate_randomisation_schedule(spec)


def test_rejects_non_balanced_block_size():
    spec = _spec()
    spec["allocation"]["allowed_block_sizes"] = [4, 6]
    with pytest.raises(ValueError, match="block size must be divisible"):
        generate_randomisation_schedule(spec)
