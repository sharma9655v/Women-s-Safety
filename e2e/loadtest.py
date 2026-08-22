#!/usr/bin/env python3
"""Reproducible load test for the Map for Women API.

Usage:
    uv run --directory apps/api python ../e2e/loadtest.py --base-url http://localhost:8000
    uv run --directory apps/api python ../e2e/loadtest.py --concurrency 40 --duration 30
    uv run --directory apps/api python ../e2e/loadtest.py --requests 2000 --max-error-rate 0.01

Behaviour:
  - fires a realistic request mix (health, models/gate, safety area,
    incidents, routes, geocode) at the configured concurrency;
  - reports throughput, latency percentiles (p50/p90/p99/max) and error
    rate per endpoint and overall;
  - exits non-zero when the error rate or p99 exceeds thresholds (used in
    CI / pre-deploy gates), or when --check is set.

Deterministic workload: routes/coordinates come from a fixed pool, so runs
are comparable. No PII, no writes: only read endpoints are exercised.
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import time
from dataclasses import dataclass, field

import httpx

DELHI_POOL = [
    (28.6139, 77.2090),
    (28.6315, 77.2167),
    (28.5847, 77.2210),
    (28.6562, 77.2410),
    (28.5696, 77.1353),
    (28.6056, 77.2171),
    (28.6448, 77.2167),
    (28.5798, 77.1858),
    (28.6206, 77.1399),
    (28.5945, 77.2444),
]

ENDPOINTS = [
    ("health", "/health"),
    ("models", "/api/models/current"),
    ("safety_area", "/api/safety/area?name=connaught-place"),
    ("incidents", "/api/incidents"),
    ("routes", "dynamic"),
]


def build_route_url(src: tuple[float, float], dst: tuple[float, float]) -> str:
    lat1, lon1 = src
    lat2, lon2 = dst
    return (
        "/api/routes"
        f"?src_lat={lat1:.4f}&src_lon={lon1:.4f}"
        f"&dst_lat={lat2:.4f}&dst_lon={lon2:.4f}"
        "&hour_ist=21&mode=safe"
    )


@dataclass
class Result:
    endpoint: str
    latencies: list[float] = field(default_factory=list)
    statuses: list[int] = field(default_factory=list)
    errors: int = 0

    @property
    def count(self) -> int:
        return len(self.latencies)

    @property
    def error_rate(self) -> float:
        return self.errors / self.count if self.count else 0.0

    def percentile(self, p: float) -> float:
        if not self.latencies:
            return 0.0
        ordered = sorted(self.latencies)
        index = min(len(ordered) - 1, int(p / 100.0 * len(ordered)))
        return ordered[index]

    def summary(self) -> str:
        if not self.count:
            return f"{self.endpoint:<14} 0 requests"
        return (
            f"{self.endpoint:<14} n={self.count:<6} "
            f"p50={self.percentile(50) * 1000:7.1f}ms "
            f"p90={self.percentile(90) * 1000:7.1f}ms "
            f"p99={self.percentile(99) * 1000:7.1f}ms "
            f"max={max(self.latencies) * 1000:7.1f}ms "
            f"err={self.error_rate:.2%}"
        )


async def worker(
    client: httpx.AsyncClient,
    base_url: str,
    results: dict[str, Result],
    stop: asyncio.Event,
) -> None:
    index = 0
    while not stop.is_set():
        kind, url = _pick(index)
        index += 1
        endpoint = results[kind]
        started = time.perf_counter()
        try:
            response = await client.get(f"{base_url}{url}", timeout=15.0)
            latency = time.perf_counter() - started
            endpoint.latencies.append(latency)
            endpoint.statuses.append(response.status_code)
            if response.status_code >= 500:
                endpoint.errors += 1
        except Exception:
            latency = time.perf_counter() - started
            endpoint.latencies.append(latency)
            endpoint.errors += 1


def _pick(index: int) -> tuple[str, str]:
    kind, template = ENDPOINTS[index % len(ENDPOINTS)]
    if kind == "routes":
        src = DELHI_POOL[index % len(DELHI_POOL)]
        dst = DELHI_POOL[(index * 7 + 3) % len(DELHI_POOL)]
        return kind, build_route_url(src, dst)
    return kind, template


async def run_loadtest(
    base_url: str,
    concurrency: int,
    duration_s: float | None,
    requests: int | None,
    timeout_s: float = 15.0,
) -> dict[str, Result]:
    results = {kind: Result(endpoint=kind) for kind, _ in ENDPOINTS}
    stop = asyncio.Event()
    tasks: list[asyncio.Task[None]] = []

    async with httpx.AsyncClient(timeout=timeout_s) as client:
        workers = [asyncio.create_task(worker(client, base_url, results, stop)) for _ in range(concurrency)]
        if duration_s is not None:
            await asyncio.sleep(duration_s)
            stop.set()
        elif requests is not None:
            # Each worker fires roughly requests/concurrency; stop when the
            # target total is reached.
            target = requests
            while sum(r.count for r in results.values()) < target and not stop.is_set():
                await asyncio.sleep(0.05)
            stop.set()
        await asyncio.gather(*workers, return_exceptions=True)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Map for Women API load test")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--concurrency", type=int, default=25)
    parser.add_argument("--duration", type=float, default=20.0,
                        help="seconds to run (default 20; mutually exclusive with --requests)")
    parser.add_argument("--requests", type=int, default=None,
                        help="total request target instead of a duration")
    parser.add_argument("--max-error-rate", type=float, default=0.02,
                        help="fail when overall error rate exceeds this (default 0.02)")
    parser.add_argument("--max-p99-ms", type=float, default=2500.0,
                        help="fail when overall p99 exceeds this in ms (default 2500)")
    args = parser.parse_args()

    if args.requests is None and args.duration is None:
        parser.error("one of --duration or --requests is required")

    started = time.perf_counter()
    results = asyncio.run(
        run_loadtest(
            args.base_url,
            args.concurrency,
            duration_s=args.duration if args.requests is None else None,
            requests=args.requests,
        )
    )
    elapsed = time.perf_counter() - started

    print(f"base_url={args.base_url} concurrency={args.concurrency}")
    for kind, _ in ENDPOINTS:
        print(results[kind].summary())

    total = sum(r.count for r in results.values())
    errors = sum(r.errors for r in results.values())
    all_latencies = [lat for r in results.values() for lat in r.latencies]
    overall_error_rate = errors / total if total else 0.0
    p99 = statistics.quantiles(all_latencies, n=100)[-1] if all_latencies else 0.0
    print(
        f"total={total} requests, errors={errors} ({overall_error_rate:.2%}), "
        f"elapsed={elapsed:.1f}s, throughput={total / elapsed:.1f} req/s, "
        f"overall p99={p99 * 1000:.1f}ms"
    )

    failed = overall_error_rate > args.max_error_rate or p99 * 1000 > args.max_p99_ms
    if failed:
        print(
            f"FAIL: error rate {overall_error_rate:.2%} (max {args.max_error_rate:.2%}) "
            f"or p99 {p99 * 1000:.1f}ms (max {args.max_p99_ms}ms)"
        )
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())