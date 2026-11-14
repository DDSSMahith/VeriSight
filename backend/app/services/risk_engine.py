from app.schemas import DetectionResult, Verdict


def model_verdict(detection: DetectionResult) -> tuple[Verdict, str]:
    """The installed model has no validated decision policy for this application."""
    if detection.status != "complete" or detection.ai_score is None:
        return "inconclusive", detection.message
    if detection.stability == "sensitive":
        return (
            "inconclusive",
            "The model changed its answer after resizing or compression. This result is unreliable; check the original source.",
        )
    return (
        "inconclusive",
        (
            "We can’t reliably determine whether this image is real or AI-generated. "
            "The installed model has not passed independent validation for this app, "
            "and face-swap detection is not available. See the measured checks below."
        ),
    )
