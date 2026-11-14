"""Deterministic regional measurements, not a learned tamper/localization detector."""

import base64
import io
import logging

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app.schemas import SpatialAnalysis, SpatialMetric

logger = logging.getLogger(__name__)
GRID = 8
MAX_SIDE = 1024


def _entropy(tile: np.ndarray) -> float:
    histogram = np.histogram(tile, bins=32, range=(0, 256))[0]
    probabilities = histogram[histogram > 0] / tile.size
    return float(-np.sum(probabilities * np.log2(probabilities)))


def _tiles(array: np.ndarray):
    y_edges = np.linspace(0, array.shape[0], GRID + 1, dtype=int)
    x_edges = np.linspace(0, array.shape[1], GRID + 1, dtype=int)
    for row in range(GRID):
        for col in range(GRID):
            yield array[y_edges[row] : y_edges[row + 1], x_edges[col] : x_edges[col + 1]]


def _metric(key, name, values, value, unit, value_label, method, limitation):
    values = np.asarray(values, dtype=np.float64)
    minimum, maximum, median = float(values.min()), float(values.max()), float(np.median(values))
    highest = int(values.argmax())
    summary = (
        f"All 64 regions have the same measured value ({maximum:.2f} {unit})."
        if maximum - minimum < 0.005
        else f"Highest measurement: row {highest // GRID + 1}, column {highest % GRID + 1} "
        f"({maximum:.2f} {unit}); typical region: {median:.2f} {unit}. "
        f"The regional range is {maximum - minimum:.2f} {unit}."
    )
    return SpatialMetric(
        id=key,
        name=name,
        value=round(float(value), 4),
        unit=unit,
        value_label=value_label,
        minimum=round(minimum, 4),
        maximum=round(maximum, 4),
        median=round(median, 4),
        cells=np.round(values, 4).tolist(),
        summary=summary,
        method=method,
        limitation=limitation,
    )


def measure_spatial(content: bytes, media_kind: str) -> SpatialAnalysis:
    if media_kind != "image":
        return SpatialAnalysis(
            status="unsupported", message="Spatial measurements require a still image."
        )
    try:
        with Image.open(io.BytesIO(content)) as source:
            if getattr(source, "n_frames", 1) > 1:
                return SpatialAnalysis(
                    status="unsupported", message="Animated images are not measured."
                )
            if min(source.size) < 64:
                return SpatialAnalysis(
                    status="unsupported",
                    message="Each side must be at least 64 pixels for regional measurements.",
                )
            image = ImageOps.exif_transpose(source)
            original_size = image.size
            # Limit calculation size; preserve aspect ratio and document this below.
            image.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
            if min(image.size) < GRID * 2:
                return SpatialAnalysis(
                    status="unsupported",
                    message="This image is too narrow for regional comparison at the analysis resolution.",
                )
            rgba = image.convert("RGBA")
            background = Image.new("RGBA", rgba.size, "white")
            image = Image.alpha_composite(background, rgba).convert("RGB")
        rgb = np.asarray(image, dtype=np.float32)
        # Display-encoded brightness, deliberately not physical scene illumination.
        gray = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
        kernel = np.exp(-(np.arange(-3, 4, dtype=np.float32) ** 2) / 2)
        kernel /= kernel.sum()
        padded = np.pad(gray, ((0, 0), (3, 3)), mode="edge")
        horizontal = sum(kernel[i] * padded[:, i : i + gray.shape[1]] for i in range(7))
        padded = np.pad(horizontal, ((3, 3), (0, 0)), mode="edge")
        blurred = sum(kernel[i] * padded[i : i + gray.shape[0], :] for i in range(7))
        residual = gray - blurred
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=90, subsampling=0)
        with Image.open(io.BytesIO(buffer.getvalue())) as compressed:
            difference = np.abs(rgb - np.asarray(compressed.convert("RGB"), dtype=np.float32)).mean(
                axis=2
            )
        brightness = [float(tile.mean()) for tile in _tiles(gray)]
        entropy = [_entropy(tile) for tile in _tiles(gray)]
        detail = [float(np.sqrt(np.mean(tile**2))) for tile in _tiles(residual)]
        compression = [float(tile.mean()) for tile in _tiles(difference)]
        metrics = [
            _metric(
                "brightness",
                "Brightness variation",
                brightness,
                np.percentile(brightness, 90) - np.percentile(brightness, 10),
                "levels",
                "Regional 90th–10th percentile gap",
                "Mean display brightness per region: 0.2126R + 0.7152G + 0.0722B, on a 0–255 scale. The card reports the 90th–10th percentile gap across regions.",
                "Brightness is affected by object colors, shadows, and exposure. This does not estimate light-source direction or establish physically inconsistent lighting.",
            ),
            _metric(
                "texture",
                "Texture variation",
                entropy,
                np.median(entropy),
                "bits",
                "Median regional entropy",
                "Shannon entropy of a 32-bin brightness histogram in each region (0–5 bits). More varied brightness values produce a higher reading.",
                "Natural materials, hair, text, blur, and noise all change entropy. High or low entropy alone does not indicate synthesis or an edit.",
            ),
            _metric(
                "detail",
                "Fine-detail / noise residual",
                detail,
                np.median(detail),
                "levels RMS",
                "Median regional residual",
                "Root-mean-square difference between brightness and a Gaussian-blurred copy (sigma 1 analysis pixel, 7-tap separable kernel, replicated edges), measured per region.",
                "This mixes texture, edges, sharpening, and noise. It is not a sensor-noise estimate or a camera fingerprint; differences need contextual review.",
            ),
            _metric(
                "compression",
                "JPEG re-save difference",
                compression,
                np.mean(compression),
                "levels",
                "Mean regional absolute difference",
                "Mean absolute RGB difference after saving the analysis image as JPEG at quality 90, with chroma subsampling disabled. Region values use a 0–255 channel scale.",
                "Detailed edges and saturated colors often change most. This is a controlled re-save experiment, not proof of a pasted region or a reconstruction of past compression.",
            ),
        ]
        preview = image.copy()
        preview.thumbnail((512, 512))
        buffer = io.BytesIO()
        preview.save(buffer, format="JPEG", quality=85)
        return SpatialAnalysis(
            status="complete",
            width=image.width,
            height=image.height,
            rows=GRID,
            columns=GRID,
            message=f"Original oriented image: {original_size[0]} × {original_size[1]}. Measurements use {image.width} × {image.height} pixels in an 8 × 8 grid. Transparent pixels are composited on white. Maps show measurements, not detected forgeries.",
            preview_data_url="data:image/jpeg;base64,"
            + base64.b64encode(buffer.getvalue()).decode("ascii"),
            metrics=metrics,
        )
    except (UnidentifiedImageError, OSError, ValueError):
        logger.exception("Spatial measurements failed")
        return SpatialAnalysis(
            status="failed", message="The image could not be decoded for regional measurements."
        )
