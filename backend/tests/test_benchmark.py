from app.benchmark import evaluate, summarize
from app.schemas import DetectionResult


def test_metrics_expose_imbalance_failures_and_extreme_errors():
    rows = [
        {"label": "real", "status": "complete", "ai_score": 0.999},
        {"label": "real", "status": "complete", "ai_score": 0.1},
        {"label": "fake", "status": "complete", "ai_score": 0.001},
        {"label": "fake", "status": "failed"},
        {"label": "fake", "status": "unsupported"},
    ]
    report = summarize(rows)
    assert report["false_positive_rate"] == 0.5
    assert report["false_negative_rate"] == 1
    assert report["balanced_accuracy"] == 0.25
    assert report["score_coverage"] == 0.6
    assert report["extreme_score_count"] == 2
    assert report["authenticity_verdict_coverage"] == 0
    assert summarize(rows[:2])["balanced_accuracy"] is None


def test_duplicate_bytes_and_missing_face_detector_are_not_scored(tmp_path):
    class Detector:
        def analyze(self, *_):
            return DetectionResult(status="complete", ai_score=0.1, message="test")

    first = tmp_path / "a.png"
    second = tmp_path / "b.png"
    first.write_bytes(b"same image")
    second.write_bytes(first.read_bytes())
    rows = [
        {"path": str(first), "task": "ai-generation", "label": "real", "group": "photos"},
        {"path": str(second), "task": "ai-generation", "label": "real", "group": "photos"},
        {"path": str(first), "task": "face-manipulation", "label": "real", "group": "faces"},
    ]
    report = evaluate(rows, Detector())
    assert report["summary"]["scored"] == 1
    assert report["summary"]["failed"] == 1
    assert report["summary"]["unsupported"] == 1
    assert report["groups"]["face-manipulation/faces"]["score_coverage"] == 0
