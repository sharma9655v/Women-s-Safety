import pytest
from app.evidence import aggregate
from app.evidence.engine import Observation
from app.risk.model import compute_segment_risk

from research.ablation import (
    NOW,
    _component_risks,
    _full_risk,
    _obs,
    recombined_risk,
)


def _evidence(observations: list[Observation]):
    return aggregate(7, observations, NOW) if observations else None


def test_component_recombination_matches_production_risk() -> None:
    """The mirrored math must reproduce compute_segment_risk exactly — this
    guarantees the ablation is measuring the real pipeline."""
    obs = [
        _obs(7, "harassment", age_hours=2, reliability=0.8),
        _obs(
            7,
            "streetlight_not_working",
            age_hours=3,
            source="street_audit",
            reliability=0.95,
            value={"working": False},
        ),
    ]
    evidence = _evidence(obs)
    context = {"road_type": "footway", "lit": "no", "nearest_emergency_m": 850.0, "hour_ist": 23}
    production = compute_segment_risk(segment_id=7, evidence=evidence, **context)
    assert recombined_risk(evidence, **context) == pytest.approx(
        production.risk_probability, abs=1e-12
    )


def test_recombination_matches_in_daytime_and_sparse() -> None:
    context = {"road_type": "footway", "lit": "yes", "nearest_emergency_m": 2500.0, "hour_ist": 12}
    production = compute_segment_risk(segment_id=8, evidence=None, **context)
    assert recombined_risk(None, **context) == pytest.approx(
        production.risk_probability, abs=1e-12
    )


def test_leave_one_out_never_increases_risk() -> None:
    obs = [_obs(9, "harassment", age_hours=1, reliability=0.9)]
    evidence = _evidence(obs)
    context = {"road_type": "footway", "lit": "no", "nearest_emergency_m": 500.0, "hour_ist": 23}
    risk, contributions = _full_risk(9, obs, **context)
    full = recombined_risk(evidence, **context)
    assert risk.risk_probability == pytest.approx(full, abs=1e-12)
    for marginal in contributions.values():
        assert marginal >= 0.0
        ablated = full - marginal
        assert ablated <= full + 1e-12


def test_present_components_have_positive_marginal_contribution() -> None:
    obs = [
        _obs(10, "harassment", age_hours=2, reliability=0.8),
        _obs(
            10,
            "streetlight_not_working",
            age_hours=1,
            reliability=0.95,
            value={"working": False},
        ),
    ]
    _, contributions = _full_risk(
        10, obs, road_type="footway", lit="no", nearest_emergency_m=850.0, hour_ist=23
    )
    assert contributions["incident"] > 0.0
    assert contributions["lighting"] > 0.0
    assert contributions["facility"] > 0.0
    assert contributions["road"] > 0.0


def test_component_risks_are_bounded() -> None:
    components = _component_risks(
        None, road_type="footway", lit="no", nearest_emergency_m=100.0, hour_ist=23
    )
    for value in components.values():
        assert 0.0 <= value <= 1.0


def test_lighting_scale_matches_night_and_day() -> None:
    obs = [_obs(11, "poor_lighting", age_hours=1, reliability=0.7)]
    night = recombined_risk(_evidence(obs), "footway", "no", 1500.0, 23)
    day = recombined_risk(_evidence(obs), "footway", "no", 1500.0, 12)
    assert night > day  # daylight halves lighting importance
