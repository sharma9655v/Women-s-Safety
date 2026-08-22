"""Input preprocessing for CV checkpoints.

The registered checkpoints expect RGB images resized to 640x360 (see
models/registry.json input_schema). Preprocessing is deliberately independent
of any ML framework: input validation + resize + normalization happen here,
so a backend only ever receives a normalized float tensor payload.
"""

from __future__ import annotations

from app.cv.interface import CVInputError

DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 360
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB decoded budget

ALLOWED_FORMATS = {"jpeg", "png", "webp"}


def validate_bytes(payload: bytes) -> None:
    """Reject empty/garbage payloads before decoding."""
    if not payload:
        raise CVInputError("image payload is empty")
    if len(payload) > MAX_IMAGE_BYTES:
        raise CVInputError(f"image exceeds {MAX_IMAGE_BYTES // (1024 * 1024)} MB")


def decode_and_preprocess(
    payload: bytes, *, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT
) -> list[list[list[float]]]:
    """Decode an image (JPEG/PNG/WebP) and return a normalized RGB float
    array of shape (H, W, 3) with values in [0, 1].

    EXIF metadata is stripped by re-encoding; the returned array is a
    plain nested list so the interface never leaks framework types.
    """
    validate_bytes(payload)
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - pillow is a hard dep
        raise CVInputError("image decoding library unavailable") from exc

    try:
        with Image.open(__import__("io").BytesIO(payload)) as img:
            fmt = (img.format or "").lower()
            if fmt not in ALLOWED_FORMATS:
                raise CVInputError(f"unsupported image format: {fmt or 'unknown'}")
            rgb: object = img.convert("RGB").resize((width, height))
            pixels = list(rgb.getdata())  # type: ignore[attr-defined]
    except CVInputError:
        raise
    except Exception as exc:
        raise CVInputError(f"could not decode image: {exc}") from exc

    n = len(pixels)
    if n != width * height:
        raise CVInputError("decoded image has unexpected dimensions")
    return [
        [[r / 255.0, g / 255.0, b / 255.0] for (r, g, b) in pixels[row * width : (row + 1) * width]]
        for row in range(height)
    ]
