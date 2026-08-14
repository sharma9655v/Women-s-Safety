from __future__ import annotations

import enum


class VerificationState(enum.StrEnum):
    """Evidence lifecycle states (design.md). Never overwrite old evidence:
    state changes create new history rows, and engine transitions return new
    objects instead of mutating inputs."""

    VERIFIED = "VERIFIED"
    REPORTED = "REPORTED"
    CORROBORATED = "CORROBORATED"
    CONFLICTING = "CONFLICTING"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


# Observation types (match safety_reports categories in data-model.md).
OBSERVATION_TYPES = {
    "streetlight_not_working",
    "poor_lighting",
    "harassment",
    "suspicious_activity",
    "blocked_sidewalk",
    "unsafe_transport",
    "road_hazard",
    "other",
}
