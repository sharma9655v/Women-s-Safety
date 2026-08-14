"""Map for Women — ML experiments.

Phase 6 of the implementation plan is *gated*: no training until a labeled
dataset threshold exists (>= 1,000 VERIFIED observations spanning >= 90 days —
see ml/gate.py). Until then this package provides:

- ml/gate.py       — gate check that blocks training (writes artifacts/gate-report.json)
- ml/eval.py       — pure-stdlib metrics (Brier, ECE, ROC-AUC, PR-AUC, F1)
- ml/dataset.py    — versioned, immutable dataset snapshots (artifacts/dataset-*.csv|json)
- ml/train.py      — refuses to run while the gate is closed (exit code 3)
- ml/model_registry.py — models/registry.json conventions; empty until first real training

Integrity rules (research-spec.md):
1. No measured result is claimed before the experiment actually runs.
2. Every metric is recorded with dataset_version + model_version.
3. The UI/routing never depends on an unregistered model: the API serves
   deterministic-baseline-v1 until an active model exists in the registry.
"""

__version__ = "0.1.0"
