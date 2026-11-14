import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.detectors.image_model import ImageDetector
from app.main import analysis_service, app
from app.schemas import DetectionResult

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_detector(monkeypatch, tmp_path):
    monkeypatch.setattr(analysis_service, "detector", ImageDetector(tmp_path))


def image_upload() -> tuple[str, bytes, str]:
    stream = io.BytesIO()
    Image.new("RGB", (64, 48), color=(18, 72, 50)).save(stream, format="PNG")
    return "evidence.png", stream.getvalue(), "image/png"


def test_health_endpoint_reports_detector_coverage() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["neural_detector"] == "unavailable"


def test_api_documentation_uses_the_public_api_prefix() -> None:
    assert client.get("/api/docs").status_code == 200
    assert client.get("/api/openapi.json").status_code == 200


def test_analysis_endpoint_returns_explainable_report() -> None:
    response = client.post("/api/v1/analyze", files={"file": image_upload()})
    assert response.status_code == 200
    report = response.json()
    assert report["media"]["dimensions"] == "64 × 48"
    assert len(report["media"]["sha256"]) == 64
    assert report["verdict"] == "inconclusive"
    assert any(item["id"] == "cryptographic-identity" for item in report["evidence"])
    assert report["limitations"]["neural_detector_available"] is False
    assert report["risk_score"] is None
    assert report["confidence"] is None
    assert report["detection"]["ai_score"] is None


def test_empty_upload_is_rejected() -> None:
    response = client.post("/api/v1/analyze", files={"file": ("empty.png", b"", "image/png")})
    assert response.status_code == 400


def test_unknown_media_is_rejected() -> None:
    response = client.post(
        "/api/v1/analyze", files={"file": ("notes.bin", b"not media", "application/octet-stream")}
    )
    assert response.status_code == 415


@pytest.mark.parametrize("score", [0.013, 0.987])
def test_inference_reaches_api_without_heuristic_mixing(monkeypatch, score):
    monkeypatch.setattr(
        analysis_service.detector,
        "analyze",
        lambda *_: DetectionResult(
            status="complete", ai_score=score, model_id="test", message="test"
        ),
    )
    response = client.post("/api/v1/analyze", files={"file": image_upload()})
    report = response.json()
    assert report["detection"]["ai_score"] == score
    assert report["risk_score"] is None
    assert report["verdict"] == "inconclusive"
    assert any(item["id"] == "model-assessment" for item in report["evidence"])
    assert any(item["id"] == "face-swap-not-tested" for item in report["evidence"])
    assert report["limitations"]["neural_detector_available"] is True


def test_damaged_image_rejected():
    response = client.post(
        "/api/v1/analyze", files={"file": ("broken.png", b"\x89PNG\r\n\x1a\ninvalid", "image/png")}
    )
    assert response.status_code == 400


def test_audio_never_receives_image_score():
    response = client.post(
        "/api/v1/analyze", files={"file": ("sample.wav", b"RIFF0000WAVE0000", "audio/wav")}
    )
    assert response.json()["detection"]["status"] == "unsupported"
    assert response.json()["risk_score"] is None
    assert response.json()["spatial_analysis"]["status"] == "unsupported"


def test_spatial_metrics_run_without_a_model_and_are_in_downloadable_report():
    stream = io.BytesIO()
    Image.new("RGB", (128, 128), color=(128, 128, 128)).save(stream, format="PNG")
    response = client.post(
        "/api/v1/analyze", files={"file": ("gray.png", stream.getvalue(), "image/png")}
    )
    report = response.json()
    assert report["detection"]["status"] == "unavailable"
    assert report["spatial_analysis"]["status"] == "complete"
    assert len(report["spatial_analysis"]["metrics"]) == 4
    assert any(item["id"] == "spatial-brightness" for item in report["evidence"])
    assert report["risk_score"] is None
