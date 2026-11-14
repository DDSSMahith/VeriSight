import io

import pytest
from PIL import Image

from app.detectors import image_model


def image_bytes():
    buffer = io.BytesIO()
    Image.new("RGB", (240, 180), "gray").save(buffer, format="PNG")
    return buffer.getvalue()


def test_original_score_is_not_overridden_by_degraded_copies():
    class Runtime:
        def __init__(self):
            self.scores = iter([0.95, 0.89, 0.06])

        def predict(self, image):
            return next(self.scores), [0.91, 0.95, 0.97]

    detector = image_model.ImageDetector()
    detector.model = Runtime()
    result = detector.analyze(image_bytes(), "image")
    assert result.status == "complete"
    assert result.ai_score == 0.95
    assert result.check_scores["resize-128"] == 0.06
    assert result.stability == "sensitive"
    assert result.calibrated is False
    assert result.model_id == image_model.MODEL_ID
    assert len(result.crop_scores) == 3


def test_inference_failure_does_not_return_a_fallback_score():
    class BrokenRuntime:
        def predict(self, image):
            raise ValueError("bad logits")

    detector = image_model.ImageDetector()
    detector.model = BrokenRuntime()
    result = detector.analyze(image_bytes(), "image")
    assert result.status == "failed"
    assert result.ai_score is None
    assert result.check_scores == {}


def test_compact_runtime_skips_the_slowest_recheck_but_preserves_original():
    class Runtime:
        def __init__(self):
            self.scores = iter([0.956, 0.894])

        def predict(self, image):
            return next(self.scores), [0.99, 0.02, 0.98]

    detector = image_model.ImageDetector(runtime_name="gguf")
    detector.model = Runtime()
    result = detector.analyze(image_bytes(), "image")
    assert result.status == "complete"
    assert result.ai_score == 0.956
    assert result.check_scores == {"original": 0.956, "jpeg-85": 0.894}
    assert result.model_id == "abacusai/Smaug-AI-Image-Detector-GGUF"
    assert "resize-128" not in result.check_scores


def test_tampered_bundle_never_instantiates_runtime(tmp_path, monkeypatch):
    (tmp_path / "revision.txt").write_text(image_model.REVISION)
    (tmp_path / "weights").write_bytes(b"tampered")
    monkeypatch.setattr(image_model, "FILES", {"weights": "0" * 64})
    monkeypatch.setattr(image_model, "SmaugRuntime", lambda _: pytest.fail("unverified load"))
    detector = image_model.ImageDetector(tmp_path)
    detector.load()
    assert not detector.ready


def test_runtime_averages_logits_not_probabilities_or_maximum():
    torch = pytest.importorskip("torch")
    from app.detectors.smaug_runtime import SmaugRuntime

    class Encoder:
        def encode(self, views, **kwargs):
            assert len(views) == 3
            return torch.tensor([[-4.0], [1.0], [1.0]])

    runtime = SmaugRuntime.__new__(SmaugRuntime)
    runtime.model = Encoder()
    score, crops = runtime.predict(Image.new("RGB", (600, 600)))
    assert score == pytest.approx(torch.sigmoid(torch.tensor(-2 / 3)).item())
    assert score < 0.5  # Mean probabilities or max would incorrectly favor AI here.
    assert len(crops) == 3
