"""In-process metrics store (Prometheus text format).

Tracks request counts/latency/errors, database latency, CV inference
latency/failures, and model-state gauges. Exposed at GET /metrics.

Design constraints:
  - never log or expose request bodies, query strings, tokens, or PII;
  - histogram buckets are fixed so output is deterministic;
  - pure stdlib (no external metrics dependency).
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable
from threading import Lock

LATENCY_BUCKETS_S = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


class _Histogram:
    def __init__(self) -> None:
        self.buckets = [0] * (len(LATENCY_BUCKETS_S) + 1)
        self.sum_s = 0.0
        self.count = 0

    def observe(self, seconds: float) -> None:
        for i, upper in enumerate(LATENCY_BUCKETS_S):
            if seconds <= upper:
                self.buckets[i] += 1
                break
        else:
            self.buckets[-1] += 1
        self.sum_s += seconds
        self.count += 1


class MetricsStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: defaultdict[str, int] = defaultdict(int)
        self._histograms: dict[str, _Histogram] = defaultdict(_Histogram)
        self._gauges: dict[str, float] = {}

    # --- counters ----------------------------------------------------------

    def incr(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[name] += amount

    # --- histograms ---------------------------------------------------------

    def observe(self, name: str, seconds: float) -> None:
        with self._lock:
            self._histograms[name].observe(max(0.0, seconds))

    # --- gauges --------------------------------------------------------------

    def set_gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    # --- rendering ------------------------------------------------------------

    def render(self) -> str:
        """Render all metrics in Prometheus text exposition format."""
        with self._lock:
            lines: list[str] = []
            for name, counter_value in sorted(self._counters.items()):
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name} {counter_value}")
            for name, hist in sorted(self._histograms.items()):
                lines.append(f"# TYPE {name} histogram")
                lines.append(f"{name}_count {hist.count}")
                lines.append(f"{name}_sum {hist.sum_s:.6f}")
                for i, upper in enumerate(LATENCY_BUCKETS_S):
                    lines.append(f'{name}_bucket{{le="{upper}"}} {hist.buckets[i]}')
                lines.append(f'{name}_bucket{{le="+Inf"}} {hist.buckets[-1]}')
            for name, gauge_value in sorted(self._gauges.items()):
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name} {gauge_value}")
            return "\n".join(lines) + "\n"


_metrics = MetricsStore()


def get_metrics() -> MetricsStore:
    return _metrics


def record_request(
    path: str,
    method: str,
    status_code: int,
    duration_s: float,
    db_duration_s: float | None = None,
) -> None:
    # Defensive: never let query strings (or anything after '?') into labels.
    path = path.split("?")[0]
    status_class = status_code // 100
    _metrics.incr("api_requests_total")
    _metrics.incr(f'api_requests_total{{path="{path}",method="{method.lower()}"}}')
    _metrics.incr(f'api_requests_total{{status="{status_class}xx"}}')
    _metrics.observe("api_request_duration_seconds", duration_s)
    if status_code >= 500:
        _metrics.incr("api_errors_total")
    if db_duration_s is not None:
        _metrics.observe("db_query_duration_seconds", db_duration_s)


def record_cv_inference(status: str, duration_s: float) -> None:
    _metrics.incr(f'cv_inference_total{{status="{status}"}}')
    _metrics.observe("cv_inference_duration_seconds", duration_s)


def record_cv_load_failure(reason: str) -> None:
    _metrics.incr("cv_load_failures_total")
    _metrics.set_gauge("cv_backend_loaded", 0.0)


def record_ingestion(outcome: str, rows: int) -> None:
    _metrics.incr(f'ingestion_total{{outcome="{outcome}"}}')
    _metrics.incr("ingestion_rows_total", rows)


def record_db_latency(seconds: float) -> None:
    _metrics.observe("db_query_duration_seconds", seconds)


def set_active_model(risk_model: str, gate_open: bool) -> None:
    _metrics.set_gauge("active_risk_model", 1.0 if risk_model else 0.0)
    _metrics.set_gauge("ml_gate_open", 1.0 if gate_open else 0.0)


def set_cv_backend_loaded(loaded: bool) -> None:
    _metrics.set_gauge("cv_backend_loaded", 1.0 if loaded else 0.0)


def timed_db(call: Callable[[], object]) -> object:
    """Measure a DB call and record latency (used by readiness probes)."""
    started = time.perf_counter()
    try:
        result = call()
    finally:
        record_db_latency(time.perf_counter() - started)
    return result
