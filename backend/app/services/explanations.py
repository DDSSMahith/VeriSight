"""Explain recorded measurements; never invent visual defects from a class score."""

from app.schemas import DetectionResult, Evidence


def explain_detection(result: DetectionResult, media_kind: str) -> list[Evidence]:
    findings = []
    if result.status == "complete" and result.ai_score is not None:
        findings.append(
            Evidence(
                id="model-assessment",
                title="An experimental model ran, but cannot verify this image",
                description="The model examined the image’s pixels. Its output has not been calibrated "
                "or independently validated for this app, so even a near-zero or near-100 score "
                "does not support a real/fake conclusion. File details do not change this output.",
                category="model",
                severity="info",
                score=0,
                observed=f"Raw AI-class output: {result.ai_score:.6f} (0–1 scale; not a confidence estimate)",
            )
        )
        if result.crop_scores:
            findings.append(
                Evidence(
                    id="model-crops",
                    title="Three parts of the original were checked",
                    description="The model checked the start, middle, and end of the image's longer "
                    "side, using overlapping square crops. Their outputs were combined into the "
                    "original-image score. These are classification scores, not locations of proven edits.",
                    observed="AI-class outputs (0–100, not confidence): "
                    + ", ".join(f"{value * 100:.2f}" for value in result.crop_scores),
                    category="model",
                    severity="info",
                    score=0,
                )
            )
        if result.check_scores:
            names = {"original": "Original", "jpeg-85": "JPEG copy", "resize-128": "Smaller copy"}
            measurements = "; ".join(
                f"{names.get(name, name)}: {value * 100:.2f}/100"
                for name, value in result.check_scores.items()
            )
            spread = (max(result.check_scores.values()) - min(result.check_scores.values())) * 100
            sensitive = result.stability == "sensitive"
            findings.append(
                Evidence(
                    id="model-stability",
                    title="Resizing or compression changed the result"
                    if sensitive
                    else "The re-check did not trigger the instability warning",
                    description=f"{measurements}. The range was {spread:.2f} points. "
                    + (
                        "The preferred class changed or the score moved by at least 60 points. "
                        "The smaller copy is only 128 × 128 pixels and can lose useful detail. "
                        "This sensitivity reduces how much we can rely on the result."
                        if sensitive
                        else "This stayed below our provisional 60-point warning threshold. It only tests "
                        "sensitivity to these two changes; it does not establish that the answer is correct."
                    ),
                    category="model",
                    severity="medium" if sensitive else "info",
                    score=0,
                )
            )
        findings.append(
            Evidence(
                id="model-explanation-limit",
                title="No specific visual defect was established",
                description="This classifier returns a score, not a description or location of an edit. "
                "It has not identified mismatched eyes, skin, lighting, or a swapped face. "
                "The file checks below are separate observations, not an explanation of the model’s internal decision.",
                category="model",
                severity="info",
                score=0,
            )
        )
    else:
        findings.append(
            Evidence(
                id="model-not-run",
                title="No AI-image assessment was produced",
                description=result.message,
                category="model",
                severity="info",
                score=0,
            )
        )
    if media_kind == "image":
        findings.append(
            Evidence(
                id="face-swap-not-tested",
                title="Face swaps were not tested",
                description="There is no face-manipulation detector in this build. An AI-generation "
                "score cannot rule out a swapped or edited face. This remains an untested part of the image.",
                category="model",
                severity="info",
                score=0,
            )
        )
    return findings
