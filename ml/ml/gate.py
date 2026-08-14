"""Training gate: never train a safety model before real labeled data exists.

The gate mirrors implementation-plan.md Phase 6: training may only start once
a labeled dataset threshold exists (>= MIN_VERIFIED_OBSERVATIONS verified
observations spanning >= MIN_SPAN_DAYS). The label of record is the evidence
engine's VERIFIED state (verification_state == 'VERIFIED'), not a guess.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import psycopg

MIN_VERIFIED_OBSERVATIONS = 1_000
MIN_SPAN_DAYS = 90
DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/mapforwomen"


@dataclass(frozen=True)
class GateReport:
    verified_observations: int
    total_observations: int
    span_days: float
    threshold_observations: int
    threshold_span_days: int
    open: bool
    reason: str
    checked_at: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _connect(database_url: str = DATABASE_URL) -> psycopg.Connection:
    conn = psycopg.connect(database_url.replace("+psycopg", ""))
    return conn


def check_gate(database_url: str = DATABASE_URL) -> GateReport:
    """Count VERIFIED observations and their time span in the evidence DB."""
    checked_at = datetime.now(UTC).isoformat(timespec="seconds")
    try:
        with _connect(database_url) as conn:
            row = conn.execute(
                """
                SELECT
                    count(*) FILTER (WHERE verification_state = 'VERIFIED') AS verified,
                    count(*) AS total,
                    COALESCE(
                        EXTRACT(EPOCH FROM (max(observed_at) - min(observed_at))) / 86400.0,
                        0.0
                    ) AS span_days
                FROM safety_observations
                """
            ).fetchone()
        verified, total, span_days = int(row[0]), int(row[1]), float(row[2])
    except psycopg.OperationalError:
        return GateReport(
            verified_observations=0,
            total_observations=0,
            span_days=0.0,
            threshold_observations=MIN_VERIFIED_OBSERVATIONS,
            threshold_span_days=MIN_SPAN_DAYS,
            open=False,
            reason="Database unreachable — gate closed.",
            checked_at=checked_at,
        )

    reasons: list[str] = []
    if verified < MIN_VERIFIED_OBSERVATIONS:
        reasons.append(f"verified observations {verified} < {MIN_VERIFIED_OBSERVATIONS}")
    if span_days < MIN_SPAN_DAYS:
        reasons.append(f"data span {span_days:.1f} days < {MIN_SPAN_DAYS}")
    return GateReport(
        verified_observations=verified,
        total_observations=total,
        span_days=span_days,
        threshold_observations=MIN_VERIFIED_OBSERVATIONS,
        threshold_span_days=MIN_SPAN_DAYS,
        open=not reasons,
        reason="; ".join(reasons) or "gate open",
        checked_at=checked_at,
    )


def write_report(report: GateReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    out = Path(__file__).parent / "artifacts" / "gate-report.json"
    report = check_gate()
    write_report(report, out)
    print(json.dumps(report.to_dict(), indent=2))
