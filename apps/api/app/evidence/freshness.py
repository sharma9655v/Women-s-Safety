from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

# Per-type exponential decay rates (1/day): freshness = exp(-lambda * age).
# Infrastructure signals decay slowly; transient incidents decay fast.
# Per-type lambdas are a design.md requirement (no universal decay rate).
TYPE_LAMBDAS: dict[str, float] = {
    "streetlight_not_working": 0.02,  # half-life ~35 days
    "poor_lighting": 0.05,  # half-life ~14 days
    "blocked_sidewalk": 0.05,  # half-life ~14 days
    "unsafe_transport": 0.10,  # half-life ~7 days
    "road_hazard": 0.10,  # half-life ~7 days
    "harassment": 0.30,  # half-life ~2.3 days
    "suspicious_activity": 0.20,  # half-life ~3.5 days
    "other": 0.10,  # half-life ~7 days
}
DEFAULT_LAMBDA = 0.10

# Evidence is considered expired once its freshness drops below this.
EXPIRY_FRESHNESS = 0.05

SECONDS_PER_DAY = 86400.0


def lambda_for(observation_type: str) -> float:
    return TYPE_LAMBDAS.get(observation_type, DEFAULT_LAMBDA)


def age_days(observed_at: datetime, now: datetime) -> float:
    if now <= observed_at:
        return 0.0
    return (now - observed_at).total_seconds() / SECONDS_PER_DAY


def freshness(observed_at: datetime, now: datetime, observation_type: str) -> float:
    """Deterministic exponential decay; clamps to [0, 1].

    Zero once the observation is past its expiry point, so EXPIRED evidence
    never contributes to scores.
    """
    if now <= observed_at:
        return 1.0
    value = math.exp(-lambda_for(observation_type) * age_days(observed_at, now))
    if value < EXPIRY_FRESHNESS:
        return 0.0
    return value


def expires_at(observed_at: datetime, observation_type: str) -> datetime:
    """When this observation's freshness falls below EXPIRY_FRESHNESS."""
    lam = lambda_for(observation_type)
    if lam <= 0.0:
        return observed_at + timedelta(days=3650)
    days = -math.log(EXPIRY_FRESHNESS) / lam
    return observed_at + timedelta(days=days)


def is_expired(observed_at: datetime, now: datetime, observation_type: str) -> bool:
    return now > expires_at(observed_at, observation_type)


def utc_now() -> datetime:
    return datetime.now(UTC)
