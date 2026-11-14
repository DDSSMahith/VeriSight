import time
import uuid
from datetime import UTC, datetime

from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.detectors.image_model import ImageDetector
from app.schemas import AnalysisLimitations, AnalysisReport, Evidence
from app.services.explanations import explain_detection
from app.services.file_inspector import inspect_file
from app.services.risk_engine import model_verdict
from app.services.spatial_analysis import measure_spatial


class AnalysisService:
    def __init__(self, detector: ImageDetector | None = None):
        self.detector = detector or ImageDetector()

    async def analyze(
        self, content: bytes, filename: str, declared_mime: str | None
    ) -> AnalysisReport:
        started = time.perf_counter()
        inspection = await run_in_threadpool(inspect_file, content, filename, declared_mime)
        detection = await run_in_threadpool(
            self.detector.analyze, content, inspection.metadata.media_kind
        )
        verdict, summary = model_verdict(detection)
        spatial = await run_in_threadpool(measure_spatial, content, inspection.metadata.media_kind)
        # Keep file heuristics separate: they are not AI probabilities.
        return AnalysisReport(
            analysis_id=str(uuid.uuid4()),
            analyzed_at=datetime.now(UTC).isoformat(),
            verdict=verdict,
            summary=summary,
            detection=detection,
            spatial_analysis=spatial,
            risk_score=None,
            confidence=None,
            media=inspection.metadata,
            evidence=explain_detection(detection, inspection.metadata.media_kind)
            + [
                Evidence(
                    id=f"spatial-{metric.id}",
                    title=metric.name,
                    description=f"{metric.summary} {metric.limitation}",
                    severity="info",
                    score=0,
                    category="visual",
                    observed=f"{metric.value_label}: {metric.value:.2f} {metric.unit}",
                )
                for metric in spatial.metrics
            ]
            + inspection.evidence,
            limitations=AnalysisLimitations(
                neural_detector_available=detection.status == "complete",
                provenance_manifest_found=inspection.provenance_found,
                notes=[
                    detection.message,
                    "This model checks AI-generated still images, not face swaps or other localized edits.",
                    "Smaug combines three image crops for each score. Scores are uncalibrated; unseen generators, screenshots, and compression may cause errors.",
                    "Our local checks found errors on heavily downsized copies. Resizing agreement is a robustness check, not an accuracy measurement.",
                    "No deployment accuracy has been established. Automatic authenticity verdicts are disabled; raw model output is diagnostic only.",
                ],
            ),
            processing_ms=round((time.perf_counter() - started) * 1000),
            engine_version=settings.version,
        )
