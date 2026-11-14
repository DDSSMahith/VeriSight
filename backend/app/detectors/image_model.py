"""Local, pinned, safetensors-only inference. Never downloads during an upload."""

import hashlib
import io
import logging
import threading
from pathlib import Path

from PIL import Image, ImageOps

from app.detectors.model_manifest import FILES, MODEL_ID, REVISION
from app.detectors.smaug_runtime import SmaugRuntime
from app.schemas import DetectionResult

MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "smaug"
logger = logging.getLogger(__name__)


class ImageDetector:
    def __init__(self, model_dir: Path = MODEL_DIR):
        self.model_dir = model_dir
        self.model = None
        self.lock = threading.Lock()
        self.message = (
            "Image detector is not loaded. Run setup-model.cmd, then restart the backend."
        )

    @property
    def ready(self) -> bool:
        return self.model is not None

    def load(self) -> None:
        try:
            import torch
            if (self.model_dir / "revision.txt").read_text().strip() != REVISION:
                raise ValueError("Model revision does not match the pinned version")
            for name, expected in FILES.items():
                with (self.model_dir / name).open("rb") as source:
                    if hashlib.file_digest(source, "sha256").hexdigest() != expected:
                        raise ValueError(f"Model checksum mismatch: {name}")
            torch.set_num_threads(4)
            self.model = SmaugRuntime(self.model_dir)
            self.message = "Smaug image detector ready on CPU. Scores are not calibrated."
        except Exception:
            logger.exception("Image detector could not load")
            self.model = None
            self.message = (
                "Image detector unavailable. Run setup-model.cmd and restart the backend."
            )

    def analyze(self, content: bytes, media_kind: str) -> DetectionResult:
        if media_kind != "image":
            return DetectionResult(
                status="unsupported",
                message="AI detection is currently available for still images only.",
            )
        if not self.ready:
            return DetectionResult(status="unavailable", message=self.message)
        try:
            with Image.open(io.BytesIO(content)) as source:
                if getattr(source, "n_frames", 1) > 1:
                    return DetectionResult(
                        status="unsupported",
                        message="Animated images aren't supported. Upload a still frame.",
                    )
                image = ImageOps.exif_transpose(source).convert("RGB")
                if min(image.size) < 64:
                    return DetectionResult(
                        status="unsupported",
                        message="This image is too small. Each side must be at least 64 pixels.",
                    )
            jpeg = io.BytesIO()
            image.save(jpeg, format="JPEG", quality=85)
            with Image.open(io.BytesIO(jpeg.getvalue())) as compressed:
                variants = [image, compressed.convert("RGB"), image.resize((128, 128))]
            with self.lock:
                outputs = [self.model.predict(variant) for variant in variants]
                scores = [output[0] for output in outputs]
            preferences = {(score > 0.5) - (score < 0.5) for score in scores}
            sensitive = max(scores) - min(scores) >= 0.6 or len(preferences) > 1
            return DetectionResult(
                status="complete",
                model_id=MODEL_ID,
                revision=REVISION,
                ai_score=scores[0],
                stability="sensitive" if sensitive else "consistent",
                check_scores=dict(zip(("original", "jpeg-85", "resize-128"), scores, strict=True)),
                crop_scores=outputs[0][1],
                method="Three 528-pixel crops per version; average crop logits, then sigmoid.",
                message=(
                    "Resizing or compression changed the model's result. Use the original score with caution; small copies can lose important detail."
                    if sensitive
                    else "Raw model score, not a verified probability. A stable score can still be wrong."
                ),
            )
        except Exception:
            logger.exception("Image inference failed")
            return DetectionResult(
                status="failed",
                model_id=MODEL_ID,
                revision=REVISION,
                message="The image detector couldn't finish. No AI score was produced.",
            )
