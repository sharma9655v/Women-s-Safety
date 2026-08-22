"""Output normalization for CV backends.

Backends return raw logits/scores; postprocessing converts them into the
stable CVPrediction shape (scores in [0, 1], confidence aggregate in [0, 1])
regardless of the framework. No thresholds are applied here — thresholds are
a product decision owned by the caller.
"""

from __future__ import annotations

import math


def sigmoid(x: float) -> float:
    """Numerically stable sigmoid."""
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def softmax(logits: list[float]) -> list[float]:
    """Numerically stable softmax."""
    if not logits:
        return []
    m = max(logits)
    exps = [math.exp(v - m) for v in logits]
    total = sum(exps)
    if total <= 0.0:
        return [1.0 / len(logits)] * len(logits)
    return [e / total for e in exps]


def normalize_classifier_scores(logits: list[float], activation: str) -> list[float]:
    """Map raw logits to [0, 1] per output unit."""
    if not logits:
        return []
    if activation == "softmax":
        return softmax(logits)
    return [sigmoid(v) for v in logits]


def aggregate_confidence(scores: list[float]) -> float:
    """Single [0, 1] confidence for a classification output.

    Uses 1 - normalized-entropy so a confident (peaky) prediction scores
    high and a flat prediction scores low. Deterministic and framework-free.
    """
    if not scores:
        return 0.0
    s = [max(0.0, min(1.0, v)) for v in scores]
    total = sum(s)
    if total <= 0.0:
        return 0.0
    probs = [v / total for v in s]
    entropy = -sum(p * math.log(p) if p > 0 else 0.0 for p in probs)
    max_entropy = math.log(len(probs))
    if max_entropy <= 0:
        return 1.0
    return max(0.0, min(1.0, 1.0 - entropy / max_entropy))
