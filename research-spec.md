# Research Specification

## Research question
How can safety-aware route recommendation remain reliable when urban safety evidence is incomplete, stale, noisy and conflicting?

## Hypotheses
H1: Dynamic evidence reduces modeled risk versus fastest-route baselines.
H2: Freshness/source reliability improves calibration.
H3: Uncertainty-aware routing is more robust to stale/conflicting evidence.
H4: Explanations improve route acceptance/trust.

## Critical experiment
Start with a verified-working streetlight observation.
Simulate failure after a time interval.
Add one report, then multiple independent reports.
Add verified repair.
Measure whether the system:
1. reduces old evidence weight,
2. increases uncertainty,
3. changes route ranking,
4. restores confidence after verification.

## Metrics
Risk reduction
Travel-time penalty
Distance penalty
ROC-AUC
PR-AUC
F1
Brier score
Expected calibration error
Route stability
User route acceptance
User trust

## Integrity
No measured result goes into the research paper until the experiment has actually run.
