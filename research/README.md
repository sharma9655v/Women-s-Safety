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
uv run python -m research.ablation    # leave-one-out component ablation (synthetic)
uv run python -m research.calibration # synthetic calibration validation (Brier/ECE)
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

## Ablation (leave-one-out, synthetic corridor at night)

Recorded run (`ablation-*.json`, 2026-08-15, `deterministic-baseline-v1`). One
synthetic corridor (footway, unlit, streetlight failure reported, one fresh
harassment report, emergency facility 850 m). The mirrored component math is
test-verified against `compute_segment_risk` (exact reproduction); the
scenario is tuned below the 1.0 clamp so marginal deltas are exact.

| component | night marginal | share | day marginal |
|---|---|---|---|
| incident evidence | 0.5866 | 61.0% | 0.4345 |
| lighting evidence | 0.3072 | 31.9% | 0.0948 |
| road infrastructure | 0.0506 | 5.3% | 0.0125 |
| facility proximity | 0.0173 | 1.8% | 0.0128 |
| **full risk** | **0.9617** | | 0.5546 |

- Night vs day on identical evidence: risk ×1.73 (night multiplier 1.35 ×
  night road factor + lit-tag).
- Sparse twin (same context, no evidence): risk 0.0679, confidence 0.25 —
  incident/lighting evidence move risk far above the no-evidence baseline
  (0.068 → 0.962).
- Route stability: on a three-candidate synthetic choice (incident-heavy /
  lighting-heavy / facility-protected no-evidence), the winner (facility-
  protected) is unchanged under every single-component ablation — no ranking
  flips. Interpretation: on this synthetic trio the recommendation rests on
  infrastructure; evidence components are second-order.
- Confidence is evidence-volume based, not component based: ablating
  facility/road/lit changes risk but never confidence.

## Calibration (synthetic ground truth)

Recorded run (`calibration-*.json`, 2026-08-15). 240 synthetic segments over a
6-level ground-truth risk grid (0.05–0.75); evidence recipes are chosen
deterministically so the model lands within ±0.08 of each level, then
measured on synthetic outcomes y ~ Bernoulli(p).

| metric | value |
|---|---|
| mean abs error (modeled vs true risk) | 0.0034 |
| Spearman ρ (modeled vs true) | 1.000 |
| Brier (vs synthetic outcomes) | 0.1809 |
| ideal Brier (mean p(1−p)) | 0.1767 |
| Brier excess over ideal | 0.0042 |
| ECE (10 equal-width bins) | 0.0034 |

Interpretation (honest): ordering is exact *by construction* (recipes tuned
per level), so ρ = 1.0 is not evidence of real-world skill. What the run does
validate is internal consistency: on synthetic ground truth the deterministic
pipeline's risk is a calibrated probability (ECE 0.003, Brier within 0.004 of
ideal). Real calibration requires observed outcomes from validated civic/NGO
feeds — gated, none exist, and none are fabricated.
