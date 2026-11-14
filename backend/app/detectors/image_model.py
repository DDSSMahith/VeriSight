"""Local, pinned, safetensors-only inference. Never downloads during an upload."""

import hashlib
import io
import logging
import os
import threading
from pathlib import Path

from PIL import Image, ImageOps

from app.detectors.model_manifest import FILES, MODEL_ID, REVISION
from app.detectors.smaug_runtime import SmaugRuntime
from app.schemas import DetectionResult

MODEL_ROOT = Path(__file__).resolve().parents[2] / "models"
MODEL_DIR = MODEL_ROOT / "smaug"
logger = logging.getLogger(__name__)


class ImageDetector:
    def __init__(self, model_dir: Path | None = None, runtime_name: str | None = None):
        self.runtime_name = runtime_name or os.environ.get("VERISIGHT_DETECTOR_RUNTIME", "torch")
        if self.runtime_name not in {"torch", "gguf"}:
            raise ValueError("VERISIGHT_DETECTOR_RUNTIME must be 'torch' or 'gguf'")
        default_dir = MODEL_ROOT / ("smaug-gguf" if self.runtime_name == "gguf" else "smaug")
        self.model_dir = model_dir or default_dir
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
            files, revision = FILES, REVISION
            if self.runtime_name == "gguf":
                from app.detectors.gguf_manifest import FILES as files
                from app.detectors.gguf_manifest import REVISION as revision
            if (self.model_dir / "revision.txt").read_text().strip() != revision:
                raise ValueError("Model revision does not match the pinned version")
            for name, expected in files.items():
                with (self.model_dir / name).open("rb") as source:
                    if hashlib.file_digest(source, "sha256").hexdigest() != expected:
                        raise ValueError(f"Model checksum mismatch: {name}")
            if self.runtime_name == "gguf":
                from app.detectors.smaug_gguf_runtime import SmaugGGUFRuntime

                self.model = SmaugGGUFRuntime(self.model_dir)
                self.message = "Compact Smaug image detector ready on CPU. Scores are not calibrated."
            else:
                import torch

                torch.set_num_threads(4)
                self.model = SmaugRuntime(self.model_dir)
                self.message = "Smaug image detector ready on CPU. Scores are not calibrated."
        except Exception:
            logger.exception("Image detector could not load")
            self.model = None
            self.message = (
                "Image detector unavailable. Run setup-model.cmd and restart the backend."
            )

    def close(self) -> None:
        if self.model is not None and hasattr(self.model, "close"):
            self.model.close()

    @property
    def model_identity(self) -> tuple[str, str]:
        if self.runtime_name == "gguf":
            from app.detectors.gguf_manifest import MODEL_ID as model_id
            from app.detectors.gguf_manifest import REVISION as revision

            return model_id, revision
        return MODEL_ID, REVISION

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
                variants = [image, compressed.convert("RGB")]
                names = ["original", "jpeg-85"]
                if self.runtime_name != "gguf":
                    variants.append(image.resize((128, 128)))
                    names.append("resize-128")
            with self.lock:
                outputs = [self.model.predict(variant) for variant in variants]
                scores = [output[0] for output in outputs]
            preferences = {(score > 0.5) - (score < 0.5) for score in scores}
            sensitive = max(scores) - min(scores) >= 0.6 or len(preferences) > 1
            model_id, revision = self.model_identity
            return DetectionResult(
                status="complete",
                model_id=model_id,
                revision=revision,
                ai_score=scores[0],
                stability="sensitive" if sensitive else "consistent",
                check_scores=dict(zip(names, scores, strict=True)),
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
            model_id, revision = self.model_identity
            return DetectionResult(
                status="failed",
                model_id=model_id,
                revision=revision,
                message="The image detector couldn't finish. No AI score was produced.",
            )
