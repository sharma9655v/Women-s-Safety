import pytest

from ml.eval import brier_score, ece, f1, pr_auc, roc_auc


def test_brier_score_perfect_and_imperfect() -> None:
    assert brier_score([1, 0, 1, 0], [1, 0, 1, 0]) == 0.0
    assert brier_score([1, 0], [0.5, 0.5]) == 0.25


def test_brier_score_length_mismatch() -> None:
    with pytest.raises(ValueError):
        brier_score([1], [0.5, 0.5])


def test_roc_auc_perfect_separation() -> None:
    labels = [0, 0, 1, 1]
    assert roc_auc(labels, [0.1, 0.2, 0.8, 0.9]) == 1.0


def test_roc_auc_reversed_is_zero() -> None:
    labels = [0, 0, 1, 1]
    assert roc_auc(labels, [0.9, 0.8, 0.2, 0.1]) == 0.0


def test_roc_auc_ties_half() -> None:
    labels = [0, 1, 0, 1]
    assert roc_auc(labels, [0.5, 0.5, 0.5, 0.5]) == pytest.approx(0.5)


def test_roc_auc_needs_both_classes() -> None:
    with pytest.raises(ValueError):
        roc_auc([1, 1], [0.9, 0.8])


def test_pr_auc_hand_computed() -> None:
    # labels [1, 0, 1, 0], scores [0.9, 0.8, 0.7, 0.1]:
    # (1,1) -> p=1, r=0.5 : 0.5*(0.5-0)*(1+1)            = 0.5
    # (1,2) -> p=0.5, r=0.5 : 0.5*(0.5-0.5)*(0.5+1)       = 0
    # (2,3) -> p=2/3, r=1.0 : 0.5*(1.0-0.5)*(2/3+0.5)     = 7/24
    # (2,4) -> p=0.5, r=1.0 : 0.5*(1.0-1.0)*(0.5+2/3)     = 0
    labels = [1, 0, 1, 0]
    scores = [0.9, 0.8, 0.7, 0.1]
    expected = 0.5 + 7 / 24
    assert pr_auc(labels, scores) == pytest.approx(expected)


def test_ece_perfectly_calibrated() -> None:
    labels = [1, 0, 1, 0]
    probs = [0.5, 0.5, 0.5, 0.5]
    assert ece(labels, probs, bins=2) == pytest.approx(0.0, abs=1e-6)


def test_ece_miscalibrated() -> None:
    labels = [1, 1, 0, 0]
    probs = [0.95, 0.95, 0.05, 0.05]
    # bin [0.9,1.0): acc 1.0, conf 0.95, weight 0.5 -> 0.025
    # bin [0.0,0.1): acc 0.0, conf 0.05, weight 0.5 -> 0.025
    assert ece(labels, probs, bins=10) == pytest.approx(0.05, abs=1e-6)


def test_f1() -> None:
    assert f1([1, 0, 1, 0, 1], [1, 0, 0, 1, 1]) == pytest.approx(2 / 3)
    assert f1([0, 0], [1, 1]) == 0.0
    assert f1([1, 1], [0, 0]) == 0.0


def test_ece_single_bin_is_absolute_error_of_mean() -> None:
    labels = [1, 0, 1]
    probs = [0.9, 0.1, 0.8]
    assert ece(labels, probs, bins=1) == pytest.approx(abs(2 / 3 - 0.6))
