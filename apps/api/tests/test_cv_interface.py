from __future__ import annotations

import base64

import pytest

from app.cv import postprocess, preprocess
from app.cv.interface import CVInputError

TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def test_validate_bytes_rejects_empty() -> None:
    with pytest.raises(CVInputError):
        preprocess.validate_bytes(b"")


def test_validate_bytes_rejects_oversized() -> None:
    with pytest.raises(CVInputError):
        preprocess.validate_bytes(b"\x00" * (preprocess.MAX_IMAGE_BYTES + 1))


def test_decode_and_preprocess_returns_expected_shape_and_range() -> None:
    array = preprocess.decode_and_preprocess(TINY_PNG)
    assert len(array) == preprocess.DEFAULT_HEIGHT
    assert len(array[0]) == preprocess.DEFAULT_WIDTH
    assert len(array[0][0]) == 3
    flat = [v for row in array for pixel in row for v in pixel]
    assert min(flat) >= 0.0
    assert max(flat) <= 1.0


def test_decode_and_preprocess_rejects_garbage() -> None:
    with pytest.raises(CVInputError):
        preprocess.decode_and_preprocess(b"this is not an image")


def test_decode_and_preprocess_rejects_unsupported_format() -> None:
    # A GIF is a valid image but not in the allowed set.
    gif = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")
    with pytest.raises(CVInputError):
        preprocess.decode_and_preprocess(gif)


def test_sigmoid_normalization_keeps_deterministic_output() -> None:
    scores = [0.5, 0.7, 0.9]
    normalized = postprocess.normalize_classifier_scores(scores, "sigmoid")
    assert len(normalized) == 3
    assert normalized == postprocess.normalize_classifier_scores(scores, "sigmoid")
    assert all(isinstance(value, float) for value in normalized)


def test_aggregate_confidence_is_entropy_based() -> None:
    # Peaky distribution -> high confidence; flat -> low; empty -> 0.
    assert postprocess.aggregate_confidence([0.0, 1.0]) == 1.0
    assert postprocess.aggregate_confidence([0.5, 0.5]) == 0.0
    assert postprocess.aggregate_confidence([]) == 0.0
