from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ARMS = ("Placebo", "Xanomeline Low Dose", "Xanomeline High Dose")
ACTIVE_ARMS = ARMS[1:]


@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: str
    label: str
    dropout_week24: float
    mnar_shift: float
    low_power: float
    high_power: float
    any_reject_probability: float
    both_reject_probability: float
    null_familywise_error: float
    mean_week24_observed_n: float
    mean_low_estimate: float
    mean_high_estimate: float
    mean_low_full_data_target: float
    mean_high_full_data_target: float
    low_bias_vs_full_data: float
    high_bias_vs_full_data: float


def _load_spec(root: Path) -> dict[str, object]:
    return json.loads((root / "spec" / "design_operating_characteristics_v0_24.json").read_text())


def _validate_spec(spec: dict[str, object]) -> None:
    allocation = spec["allocation"]
    if list(allocation) != list(ARMS):
        raise ValueError("Allocation arms/order must match the controlled three-arm family")
    if sum(int(v) for v in allocation.values()) != 254:
        raise ValueError("Controlled design allocation must total 254 randomised subjects")
    if int(spec["replicates"]) < 500:
        raise ValueError("At least 500 simulation replicates are required")
    if not math.isclose(float(spec["alpha_family"]), 0.05):
        raise ValueError("Controlled family-wise alpha must remain 0.05")
    if len(spec["scenarios"]) < 3:
        raise ValueError("At least three dropout scenarios are required")


def _arm_vector(allocation: dict[str, int]) -> np.ndarray:
    return np.concatenate([np.repeat(arm, int(allocation[arm])) for arm in ARMS])


def _ols_treatment_contrast(
    baseline: np.ndarray,
    endpoint: np.ndarray,
    arms: np.ndarray,
    active_arm: str,
) -> tuple[float, float]:
    mask = np.isfinite(endpoint) & np.isin(arms, ["Placebo", active_arm])
    y = endpoint[mask]
    b = baseline[mask]
    a = arms[mask]
    if len(y) < 12 or (a == active_arm).sum() < 5 or (a == "Placebo").sum() < 5:
        return float("nan"), float("nan")
    x = np.column_stack([
        np.ones(len(y)),
        b - np.mean(b),
        (a == active_arm).astype(float),
    ])
    xtx_inv = np.linalg.pinv(x.T @ x)
    beta = xtx_inv @ x.T @ y
    resid = y - x @ beta
    df = len(y) - x.shape[1]
    sigma2 = float(resid @ resid) / df
    se = math.sqrt(max(float(sigma2 * xtx_inv[2, 2]), 0.0))
    if se <= 0:
        return float(beta[2]), float("nan")
    z = float(beta[2]) / se
    p = 2.0 * norm.sf(abs(z))
    return float(beta[2]), float(p)


def _simulate_one(
    rng: np.random.Generator,
    spec: dict[str, object],
    scenario: dict[str, object],
    effects: dict[str, float],
) -> dict[str, float | bool]:
    allocation = {str(k): int(v) for k, v in spec["allocation"].items()}
    arms = _arm_vector(allocation)
    n = len(arms)
    baseline = rng.normal(float(spec["baseline_mean"]), float(spec["baseline_sd"]), size=n)

    rho = float(spec["within_subject_rho"])
    residual_sd = float(spec["residual_sd"])
    corr = np.array([[rho ** abs(i - j) for j in range(3)] for i in range(3)])
    cov = residual_sd**2 * corr
    eps = rng.multivariate_normal(np.zeros(3), cov, size=n)
    ramp = np.array([1.0 / 3.0, 2.0 / 3.0, 1.0])
    effect_vec = np.array([float(effects[str(a)]) for a in arms])
    latent = baseline[:, None] + effect_vec[:, None] * ramp[None, :] + eps

    dropout_p = float(scenario["dropout_week24"])
    # Monotone dropout: among subjects who drop by Week 24, approximately
    # 20% disappear before Week 8, 35% before Week 16 and the rest before Week 24.
    drops = rng.random(n) < dropout_p
    stage = rng.choice(np.array([0, 1, 2]), size=n, p=np.array([0.20, 0.35, 0.45]))
    observed = np.ones((n, 3), dtype=bool)
    for i in np.where(drops)[0]:
        observed[i, int(stage[i]) :] = False

    # Adverse MNAR stress: active-arm outcomes hidden by dropout are allowed to
    # be worse than the generated MAR trajectory. This changes the full-data
    # target but not the observed records and therefore exposes selection bias.
    full = latent.copy()
    mnar_shift = float(scenario["mnar_shift"])
    if mnar_shift:
        active = arms != "Placebo"
        hidden_w24 = ~observed[:, 2]
        full[active & hidden_w24, 2] += mnar_shift

    endpoint = latent[:, 2].copy()
    endpoint[~observed[:, 2]] = np.nan
    low_est, low_p = _ols_treatment_contrast(baseline, endpoint, arms, ACTIVE_ARMS[0])
    high_est, high_p = _ols_treatment_contrast(baseline, endpoint, arms, ACTIVE_ARMS[1])
    local_alpha = float(spec["alpha_family"]) / len(ACTIVE_ARMS)
    low_reject = bool(np.isfinite(low_p) and low_p <= local_alpha)
    high_reject = bool(np.isfinite(high_p) and high_p <= local_alpha)

    low_full = float(np.mean(full[arms == ACTIVE_ARMS[0], 2]) - np.mean(full[arms == "Placebo", 2]))
    high_full = float(np.mean(full[arms == ACTIVE_ARMS[1], 2]) - np.mean(full[arms == "Placebo", 2]))
    return {
        "low_est": low_est,
        "high_est": high_est,
        "low_full": low_full,
        "high_full": high_full,
        "low_reject": low_reject,
        "high_reject": high_reject,
        "week24_observed_n": int(observed[:, 2].sum()),
    }


def _prob_mcse(p: float, replicates: int) -> float:
    return math.sqrt(max(p * (1.0 - p), 0.0) / replicates)


def _run_scenario(
    spec: dict[str, object], scenario: dict[str, object], seed: int
) -> ScenarioResult:
    reps = int(spec["replicates"])
    alt_rng = np.random.default_rng(seed)
    null_rng = np.random.default_rng(seed + 10_000_000)
    alt_effects = {str(k): float(v) for k, v in spec["planned_week24_effects"].items()}
    null_effects = {str(k): float(v) for k, v in spec["null_week24_effects"].items()}

    alt = [_simulate_one(alt_rng, spec, scenario, alt_effects) for _ in range(reps)]
    null = [_simulate_one(null_rng, spec, scenario, null_effects) for _ in range(reps)]
    low = np.array([bool(x["low_reject"]) for x in alt])
    high = np.array([bool(x["high_reject"]) for x in alt])
    null_any = np.array([bool(x["low_reject"] or x["high_reject"]) for x in null])
    low_est = np.array([float(x["low_est"]) for x in alt])
    high_est = np.array([float(x["high_est"]) for x in alt])
    low_full = np.array([float(x["low_full"]) for x in alt])
    high_full = np.array([float(x["high_full"]) for x in alt])

    return ScenarioResult(
        scenario_id=str(scenario["id"]),
        label=str(scenario["label"]),
        dropout_week24=float(scenario["dropout_week24"]),
        mnar_shift=float(scenario["mnar_shift"]),
        low_power=float(low.mean()),
        high_power=float(high.mean()),
        any_reject_probability=float(np.logical_or(low, high).mean()),
        both_reject_probability=float(np.logical_and(low, high).mean()),
        null_familywise_error=float(null_any.mean()),
        mean_week24_observed_n=float(np.mean([int(x["week24_observed_n"]) for x in alt])),
        mean_low_estimate=float(np.nanmean(low_est)),
        mean_high_estimate=float(np.nanmean(high_est)),
        mean_low_full_data_target=float(np.mean(low_full)),
        mean_high_full_data_target=float(np.mean(high_full)),
        low_bias_vs_full_data=float(np.nanmean(low_est - low_full)),
        high_bias_vs_full_data=float(np.nanmean(high_est - high_full)),
    )


def run_design_operating_characteristics(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    spec = _load_spec(root)
    _validate_spec(spec)
    base_seed = int(spec["seed"])
    results = [
        _run_scenario(spec, scenario, base_seed + 100_000 * i)
        for i, scenario in enumerate(spec["scenarios"], start=1)
    ]
    table = pd.DataFrame([r.__dict__ for r in results])
    reps = int(spec["replicates"])
    for col in ["low_power", "high_power", "any_reject_probability", "both_reject_probability", "null_familywise_error"]:
        table[f"{col}_mcse"] = table[col].map(lambda p: _prob_mcse(float(p), reps))

    gates = spec["quality_gates"]
    checks: list[dict[str, object]] = []
    for row in table.itertuples(index=False):
        checks.append({
            "check": f"{row.scenario_id}_null_fwer",
            "passed": float(row.null_familywise_error) <= float(gates["max_null_familywise_error"]),
            "detail": f"null FWER={row.null_familywise_error:.4f} <= {float(gates['max_null_familywise_error']):.4f}",
        })
        max_mcse = max(
            float(row.low_power_mcse), float(row.high_power_mcse),
            float(row.any_reject_probability_mcse), float(row.null_familywise_error_mcse),
        )
        checks.append({
            "check": f"{row.scenario_id}_mcse",
            "passed": max_mcse <= float(gates["max_mcse_probability"]),
            "detail": f"max probability MCSE={max_mcse:.5f}",
        })

    mar = table.loc[table["mnar_shift"].eq(0)].sort_values("dropout_week24")
    monotone = bool(np.all(np.diff(mar["mean_week24_observed_n"].to_numpy()) < 0))
    checks.append({
        "check": "mar_observed_n_monotone_with_dropout",
        "passed": monotone,
        "detail": ", ".join(f"{r.dropout_week24:.0%}:{r.mean_week24_observed_n:.1f}" for r in mar.itertuples()),
    })
    checks_df = pd.DataFrame(checks)
    metrics = {
        "version": spec["version"],
        "claim": spec["claim"],
        "replicates_per_state_per_scenario": reps,
        "scenario_count": int(len(table)),
        "checks_passed": int(checks_df["passed"].sum()),
        "checks_total": int(len(checks_df)),
        "all_passed": bool(checks_df["passed"].all()),
        "max_null_familywise_error": float(table["null_familywise_error"].max()),
        "min_mean_week24_observed_n": float(table["mean_week24_observed_n"].min()),
        "max_abs_mnar_bias": float(table[["low_bias_vs_full_data", "high_bias_vs_full_data"]].abs().to_numpy().max()),
    }
    return table, checks_df, metrics


def write_design_operating_characteristics(root: Path) -> dict[str, object]:
    table, checks, metrics = run_design_operating_characteristics(root)
    out = root / "outputs"
    out.mkdir(exist_ok=True)
    table.to_csv(out / "design_operating_characteristics.csv", index=False)
    checks.to_csv(out / "design_operating_characteristics_qc.csv", index=False)
    (out / "design_operating_characteristics_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n"
    )
    lines = [
        "# Prospective design operating-characteristics summary",
        "",
        f"- Controlled claim: `{metrics['claim']}`.",
        f"- Scenarios: {metrics['scenario_count']}; Monte Carlo replicates per alternative/null state per scenario: {metrics['replicates_per_state_per_scenario']}.",
        f"- Quality checks: {metrics['checks_passed']}/{metrics['checks_total']} PASS.",
        f"- Maximum simulated null family-wise error: {metrics['max_null_familywise_error']:.4f}.",
        f"- Lowest mean Week 24 observed N across stress scenarios: {metrics['min_mean_week24_observed_n']:.1f} of 254.",
        f"- Largest absolute observed-analysis bias versus the latent full-data target across the controlled stress scenarios: {metrics['max_abs_mnar_bias']:.3f} ACTOT points.",
        "",
        "This is a prospective public-portfolio planning stress test. The longitudinal generator preserves repeated-measures correlation, but the simulated decision analysis is a Week 24 baseline-adjusted planning approximation with Bonferroni control; it is not claimed to reproduce a sponsor protocol power calculation or a full mmrm-package simulation.",
    ]
    (out / "design_operating_characteristics_summary.md").write_text("\n".join(lines) + "\n")
    if not metrics["all_passed"]:
        raise RuntimeError("Design operating-characteristics quality gate failed")
    return metrics
