# Phase 7 — Research experiments (research-spec.md)

Every number in this project is produced by a recorded run: no claimed metric
exists without its artifact. Artifacts land in `research/artifacts/` with a
timestamp and the model versions embedded.

## Run

Requires the live stack (PostGIS + OSRM) for `baselines`; `stress` and
`lifecycle` are self-contained synthetic runs.

```powershell
uv run python -m research.baselines   # B1-B5 over real OD pairs (day, hour_ist=12)
uv run python -m research.stress      # stale / missing / noisy / conflicting / day-night
uv run python -m research.lifecycle   # streetlight lifecycle (critical experiment)
```

## Baselines (H1: dynamic evidence reduces modeled risk vs shortest/fastest)

- B1 shortest — minimum distance candidate.
- B2 fastest — minimum duration candidate.
- B3 static safety — safety_priority cost, risk computed with all evidence
  treated as fresh (freshness ignored).
- B4 dynamic safety — safety_priority cost, real freshness.
- B5 dynamic + uncertainty — B4 with a doubled uncertainty weight.

Recorded run (2026-08-14, hour_ist=12, `deterministic-baseline-v1`,
`evidence-baseline-v1`):

| pair | B1 risk | B4 risk | risk reduction | time penalty | distance penalty |
|---|---|---|---|---|---|
| seeded_area_day | 0.1011 | 0.0237 | **-76.6%** | +6.6% | +6.6% |
| connaught_place | 0.0132 | 0.0132 | 0.0% | 0.0% | 0.0% |
| karol_bagh | 0.0098 | 0.0098 | 0.0% | 0.0% | 0.0% |

Interpretation (honest): where evidence exists and differentiates candidates,
safety-aware routing reduces modeled risk at a small distance/time cost; where
evidence is sparse, all baselines agree and no difference is claimed.

## Stress tests

Recorded values (`stress-*.json`): missing evidence → confidence 0.25 +
"Limited safety data"; a 600-day-old single report is fully expired and
treated as absent; fresh single report risk 0.476 / confidence 0.7; three weak
same-source reports risk 0.630 / 0.9; conflicting streetlight evidence →
confidence ×0.7 (0.56) + "Conflicting recent evidence"; night vs day ratio on
identical evidence ≈ 1.42 (night multiplier 1.35 × road-type 1.5).

## Critical experiment (streetlight lifecycle)

Recorded run (`lifecycle-*.md/.json`) on one synthetic segment:

| step | t0 freshness | confidence | uncertainty | risk | conflicts |
|---|---|---|---|---|---|
| t0 verified working | 1.000 | 0.835 | 0.300 | 0.1892 | [] |
| t30 failure reported | 0.549 | 0.475 | **0.370** | 0.2158 | ✓ |
| t31 multiple reports | 0.538 | 0.475 | 0.300 | **0.2206** | ✓ |
| t60 verified repair | 0.301 | 0.475 | 0.300 | 0.2196 | ✓ |
| t120 decayed | 0.091 | 0.404 | 0.300 | 0.1854 | ✓ |

Answers to research-spec questions: (1) old-evidence weight decays 1.000 →
0.091; (2) uncertainty rises on conflict (0.300 → 0.370); (3) risk rises with
reports (0.189 → 0.221) which shifts route ranking under the safety profile;
(4) after verified repair + decay, risk returns to the t0 baseline (0.1854 ≈
0.1892). Confidence restore is partial while the old failure evidence is still
active — the conflict penalty persists until it expires; that is honest, not a
bug.
