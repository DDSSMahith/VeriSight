import pytest

from app.schemas import DetectionResult
from app.services.risk_engine import model_verdict


@pytest.mark.parametrize(
    "score",
    [0, 0.01, 0.2, 0.5, 0.8, 0.99, 1],
)
def test_unvalidated_model_abstains_even_at_extremes(score):
    result = DetectionResult(
        status="complete", ai_score=score, stability="consistent", message="Model result"
    )
    assert model_verdict(result)[0] == "inconclusive"


@pytest.mark.parametrize("status", ["unavailable", "unsupported", "failed"])
def test_missing_inference_never_produces_a_verdict(status):
    result = DetectionResult(status=status, message="No inference")
    assert result.ai_score is None
    assert model_verdict(result) == ("inconclusive", "No inference")


def test_unstable_high_score_abstains():
    result = DetectionResult(
        status="complete", ai_score=0.99, stability="sensitive", message="Unstable"
    )
    assert model_verdict(result)[0] == "inconclusive"
