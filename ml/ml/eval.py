"""Classification metrics for safety-model evaluation.

Pure-stdlib implementations so evaluation is reproducible anywhere.
All functions take (labels, scores/predictions) arrays of equal length and
return floats in their documented ranges.
"""

from __future__ import annotations

from collections.abc import Sequence


def brier_score(labels: Sequence[float], probabilities: Sequence[float]) -> float:
    """Mean squared error between calibrated probabilities and binary labels."""
    if len(labels) != len(probabilities) or not labels:
        raise ValueError("labels and probabilities must be non-empty and equal length")
    return sum((p - y) ** 2 for y, p in zip(labels, probabilities, strict=True)) / len(labels)


def roc_auc(labels: Sequence[float], scores: Sequence[float]) -> float:
    """Area under the ROC curve (Mann-Whitney U / rank statistic)."""
    if len(labels) != len(scores) or not labels:
        raise ValueError("labels and scores must be non-empty and equal length")
    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        raise ValueError("roc_auc needs both positive and negative labels")
    order = sorted(range(len(labels)), key=lambda i: scores[i])
    ranks: dict[int, float] = {}
    i = 0
    n = len(order)
    while i < n:
        j = i
        while j + 1 < n and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        avg_rank = (i + 1 + j + 1) / 2
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    rank_sum = sum(ranks[i] for i in range(len(labels)) if labels[i])
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def pr_auc(labels: Sequence[float], scores: Sequence[float]) -> float:
    """Area under the precision-recall curve (trapezoidal)."""
    if len(labels) != len(scores) or not labels:
        raise ValueError("labels and scores must be non-empty and equal length")
    positives = sum(labels)
    if positives == 0:
        raise ValueError("pr_auc needs at least one positive label")
    order = sorted(range(len(labels)), key=lambda i: scores[i], reverse=True)
    tp = fp = 0
    prev_precision, prev_recall = 1.0, 0.0
    area = 0.0
    for i in order:
        if labels[i]:
            tp += 1
        else:
            fp += 1
        precision = tp / (tp + fp) if (tp + fp) else 1.0
        recall = tp / positives
        area += 0.5 * (recall - prev_recall) * (precision + prev_precision)
        prev_precision, prev_recall = precision, recall
    return area


def ece(labels: Sequence[float], probabilities: Sequence[float], bins: int = 10) -> float:
    """Expected calibration error over fixed confidence bins."""
    if len(labels) != len(probabilities) or not labels:
        raise ValueError("labels and probabilities must be non-empty and equal length")
    if bins < 1:
        raise ValueError("bins must be >= 1")
    edges = [i / bins for i in range(bins + 1)]
    pairs = list(zip(labels, probabilities, strict=True))
    total = len(pairs)
    error = 0.0
    for idx in range(len(edges) - 1):
        lo, hi = edges[idx], edges[idx + 1]
        members = [(y, p) for y, p in pairs if (lo <= p < hi) or (hi == 1.0 and p == 1.0)]
        if members:
            acc = sum(y for y, _ in members) / len(members)
            conf = sum(p for _, p in members) / len(members)
            error += (len(members) / total) * abs(acc - conf)
    return error


def f1(labels: Sequence[float], predictions: Sequence[int]) -> float:
    """F1 score at a fixed decision threshold."""
    if len(labels) != len(predictions) or not labels:
        raise ValueError("labels and predictions must be non-empty and equal length")
    tp = sum(1 for y, p in zip(labels, predictions, strict=True) if p and y)
    fp = sum(1 for y, p in zip(labels, predictions, strict=True) if p and not y)
    fn = sum(1 for y, p in zip(labels, predictions, strict=True) if not p and y)
    if tp + fp == 0 or tp + fn == 0:
        return 0.0
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)
