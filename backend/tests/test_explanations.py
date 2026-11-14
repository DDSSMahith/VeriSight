from app.schemas import DetectionResult
from app.services.explanations import explain_detection


def test_explanation_contains_measured_change_and_explicit_scope():
    result = DetectionResult(
        status="complete",
        ai_score=0.23,
        message="test",
        stability="sensitive",
        check_scores={"original": 0.23, "jpeg-85": 0.999, "resize-128": 0.15},
    )
    findings = {e.id: e for e in explain_detection(result, "image")}
    assert "99.90/100" in findings["model-stability"].description
    assert "84.90 points" in findings["model-stability"].description
    assert findings["model-stability"].severity == "medium"
    assert "not identified" in findings["model-explanation-limit"].description
    assert "face-swap-not-tested" in findings


def test_failure_does_not_invent_model_measurements():
    result = DetectionResult(status="failed", message="Could not decode")
    findings = {e.id: e for e in explain_detection(result, "image")}
    assert findings["model-not-run"].description == "Could not decode"
    assert "model-stability" not in findings
    assert "model-assessment" not in findings
