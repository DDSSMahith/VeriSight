import io

import numpy as np
import pytest
from PIL import Image

from app.services.spatial_analysis import measure_spatial


def encode(array):
    stream = io.BytesIO()
    Image.fromarray(array.astype(np.uint8)).save(stream, format="PNG")
    return stream.getvalue()


def metrics(array):
    report = measure_spatial(encode(array), "image")
    assert report.status == "complete"
    assert report.preview_data_url.startswith("data:image/jpeg;base64,")
    assert report.rows == report.columns == 8
    for metric in report.metrics:
        assert len(metric.cells) == 64
        assert np.isfinite(metric.cells).all()
    return {metric.id: metric for metric in report.metrics}


def test_constant_image_has_no_texture_or_regional_brightness_variation():
    result = metrics(np.full((256, 256, 3), 128))
    assert result["brightness"].value == pytest.approx(0, abs=0.001)
    assert result["brightness"].median == pytest.approx(128, abs=0.001)
    assert result["texture"].value == 0
    assert result["detail"].value == pytest.approx(0, abs=0.001)
    assert result["compression"].value == 0


def test_brightness_step_is_localized_without_claiming_lighting_forgery():
    image = np.full((256, 256, 3), 20)
    image[:, 128:] = 220
    metric = metrics(image)["brightness"]
    assert metric.value == pytest.approx(200, abs=0.01)
    assert metric.cells[0] == pytest.approx(20, abs=0.01)
    assert metric.cells[7] == pytest.approx(220, abs=0.01)
    assert "does not estimate light-source direction" in metric.limitation


def test_texture_and_residual_locate_a_noisy_patch():
    image = np.full((256, 256), 128, dtype=np.uint8)
    image[128:, 128:] = np.random.default_rng(42).integers(0, 256, (128, 128), dtype=np.uint8)
    result = metrics(image)
    assert result["texture"].cells[63] > result["texture"].cells[0] + 4
    assert result["detail"].cells[63] > result["detail"].cells[0] + 40
    assert result["compression"].cells[63] > result["compression"].cells[0]
    assert "not a sensor-noise estimate" in result["detail"].limitation


def test_image_orientation_and_working_resolution_are_recorded():
    stream = io.BytesIO()
    image = Image.new("RGB", (2048, 1024), "gray")
    exif = Image.Exif()
    exif[274] = 6
    image.save(stream, format="JPEG", exif=exif)
    result = measure_spatial(stream.getvalue(), "image")
    assert (result.width, result.height) == (512, 1024)
    assert "1024 × 2048" in result.message


def test_unavailable_cases_do_not_produce_fake_measurements():
    assert measure_spatial(b"audio", "audio").status == "unsupported"
    assert measure_spatial(encode(np.zeros((32, 32))), "image").status == "unsupported"
    assert measure_spatial(b"broken", "image").status == "failed"
