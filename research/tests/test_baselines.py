import pytest

from research.baselines import _baseline_cost


def test_baseline_cost_monotonic_in_each_component() -> None:
    base = _baseline_cost((1.0, 1.0, 1.0, 0.8), 1000.0, 800.0, 0.05, 0.3)
    assert _baseline_cost((1.0, 1.0, 1.0, 0.8), 2000.0, 800.0, 0.05, 0.3) > base
    assert _baseline_cost((1.0, 1.0, 1.0, 0.8), 1000.0, 1600.0, 0.05, 0.3) > base
    assert _baseline_cost((1.0, 1.0, 1.0, 0.8), 1000.0, 800.0, 0.5, 0.3) > base
    assert _baseline_cost((1.0, 1.0, 1.0, 0.8), 1000.0, 800.0, 0.05, 0.9) > base


def test_baseline_cost_hand_computed() -> None:
    # 1000m + 800s*1.4m/s + 0.05*4000m + 0.8*0.3*400m (uncertainty weight 0.8)
    expected = 1000.0 + 800.0 * 1.4 + 0.05 * 4000.0 + 0.8 * 0.3 * 400.0
    assert _baseline_cost((1.0, 1.0, 1.0, 0.8), 1000.0, 800.0, 0.05, 0.3) == pytest.approx(expected)


def test_risk_term_scales_with_weights() -> None:
    # Risk 0.1 vs 0.2 with risk weight 2.0 must differ by 0.1*4000*2 = 800m.
    low = _baseline_cost((0.6, 1.0, 2.0, 1.5), 1000.0, 800.0, 0.1, 0.3)
    high = _baseline_cost((0.6, 1.0, 2.0, 1.5), 1000.0, 800.0, 0.2, 0.3)
    assert high - low == pytest.approx(0.1 * 4000.0 * 2.0)
