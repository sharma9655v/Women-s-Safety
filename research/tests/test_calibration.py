import pytest

from research.calibration import (
    TRUE_RISK_GRID,
    _model_risk,
    _outcome,
    _recipe_for,
    brier_score,
    expected_calibration_error,
    run_calibration,
    spearman_rho,
)


def test_brier_score_hand_computed() -> None:
    # Perfect predictions on certain outcomes: Brier = 0.
    assert brier_score([1.0, 0.0], [1.0, 0.0]) == pytest.approx(0.0)
    # Always predicting 0.5 against two certain outcomes: 0.25 each.
    assert brier_score([0.5, 0.5], [1.0, 0.0]) == pytest.approx(0.25)


def test_brier_penalizes_wrong_direction() -> None:
    bad = brier_score([0.9, 0.9], [0.0, 0.0])
    good = brier_score([0.1, 0.1], [0.0, 0.0])
    assert bad > good


def test_ece_zero_when_perfectly_calibrated() -> None:
    risks = [0.05, 0.15, 0.30, 0.45, 0.60, 0.75]
    assert expected_calibration_error(risks, risks, bins=10) == pytest.approx(0.0)


def test_ece_positive_when_miscalibrated() -> None:
    risks = [0.9, 0.9, 0.9]
    truths = [0.1, 0.1, 0.1]
    assert expected_calibration_error(risks, truths, bins=10) > 0.0


def test_ece_empty_input_is_zero() -> None:
    assert expected_calibration_error([], []) == 0.0


def test_spearman_monotone_is_one() -> None:
    pairs = [(0.05, 0.1), (0.3, 0.3), (0.7, 0.9)]
    assert spearman_rho(pairs) == pytest.approx(1.0)


def test_spearman_inverse_is_minus_one() -> None:
    pairs = [(0.7, 0.1), (0.3, 0.3), (0.05, 0.9)]
    assert spearman_rho(pairs) == pytest.approx(-1.0)


def test_spearman_short_input_is_zero() -> None:
    assert spearman_rho([(0.5, 0.5)]) == 0.0


def test_every_grid_level_is_reachable() -> None:
    for p in TRUE_RISK_GRID:
        found = _recipe_for(9999, p)
        assert found is not None, f"no recipe for true risk {p}"
        recipe, risk = found
        assert abs(risk.risk_probability - p) <= 0.08
        assert recipe is not None


def test_outcomes_are_deterministic_and_bounded() -> None:
    first = _outcome(42, 0.5, seed=20260814)
    again = _outcome(42, 0.5, seed=20260814)
    assert first == again
    assert first in (0.0, 1.0)


def test_run_is_deterministic_and_sane() -> None:
    run = run_calibration()
    assert run["n_segments"] > 0
    assert run["mae_risk_vs_truth"] <= 0.08
    assert run["spearman_rho_risk_vs_truth"] >= 0.99
    assert run["brier_excess_over_ideal"] >= 0.0
    assert run["ece_10_bins_risk_vs_truth"] >= 0.0
    assert run["n_segments"] == len(TRUE_RISK_GRID) * 40


def test_model_risk_is_bounded() -> None:
    risk = _model_risk(1, (3, 6.0, 0.8, 800.0, "footway", "no", True))
    assert 0.0 <= risk.risk_probability <= 1.0
