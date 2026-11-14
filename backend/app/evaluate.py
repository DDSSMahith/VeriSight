"""Reproducible smoke evaluation, not an independent accuracy benchmark.

Run: python -m app.evaluate --download (inside the backend environment)
Then rerun offline without --download. Results include every failure.
"""

import argparse
import hashlib
import io
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
from PIL import Image

from app.detectors.image_model import MODEL_ID, REVISION, ImageDetector
from app.services.risk_engine import model_verdict

ROOT = Path(__file__).resolve().parents[1] / "evaluation"
PHOTO_BASE = "https://raw.githubusercontent.com/scikit-image/scikit-image/v0.24.0/skimage/data/"
AI_BASE = "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/"
SAMPLES = [
    ("astronaut.png", 0, PHOTO_BASE + "astronaut.png"),
    ("camera.png", 0, PHOTO_BASE + "camera.png"),
    ("chelsea.png", 0, PHOTO_BASE + "chelsea.png"),
    ("text2img-1.png", 1, AI_BASE + "text2img-1.png"),
    ("sdxl-text2img.png", 1, AI_BASE + "sdxl-text2img.png"),
    ("text2img-vader.png", 1, AI_BASE + "text2img-vader.png"),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    samples = ROOT / "samples"
    samples.mkdir(parents=True, exist_ok=True)
    if args.download:
        with httpx.Client(follow_redirects=True, timeout=60) as client:
            for name, _, url in SAMPLES:
                response = client.get(url)
                response.raise_for_status()
                (samples / name).write_bytes(response.content)
    detector = ImageDetector()
    detector.load()
    if not detector.ready:
        raise RuntimeError(detector.message)
    rows = []
    for name, expected, url in SAMPLES:
        content = (samples / name).read_bytes()
        variants = [("original", content)]
        with Image.open(io.BytesIO(content)) as source:
            rgb = source.convert("RGB")
            for quality in (85, 50):
                buffer = io.BytesIO()
                rgb.save(buffer, format="JPEG", quality=quality)
                variants.append((f"jpeg-{quality}", buffer.getvalue()))
            buffer = io.BytesIO()
            rgb.resize((128, 128)).save(buffer, format="PNG")
            variants.append(("resize-128", buffer.getvalue()))
        for variant, data in variants:
            result = detector.analyze(data, "image")
            if result.status != "complete":
                raise RuntimeError(f"{name}: {result.message}")
            row = {
                "file": name,
                "variant": variant,
                "expected_ai": expected,
                "source": url,
                "sha256": hashlib.sha256(data).hexdigest(),
                "ai_score": result.ai_score,
                "verdict": model_verdict(result)[0],
                "stability": result.stability,
                "check_scores": result.check_scores,
            }
            rows.append(row)
            print(
                f"{name:24} {variant:12} expected={expected} score={result.ai_score:.6f}",
                flush=True,
            )
    original = [r for r in rows if r["variant"] == "original"]
    results = {
        "evaluated_at": datetime.now(UTC).isoformat(),
        "model_id": MODEL_ID,
        "revision": REVISION,
        "limitation": "Six public examples; unknown training overlap. Transformations are correlated. This is a smoke check, NOT deployment accuracy or calibration.",
        "original_count": len(original),
        "original_correct_at_0_5": sum(
            (r["ai_score"] >= 0.5) == bool(r["expected_ai"]) for r in original
        ),
        "original_false_positives": sum(
            r["ai_score"] >= 0.5 and r["expected_ai"] == 0 for r in original
        ),
        "original_false_negatives": sum(
            r["ai_score"] < 0.5 and r["expected_ai"] == 1 for r in original
        ),
        "rows": rows,
    }
    (ROOT / "smoke-results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in results.items() if k != "rows"}, indent=2))


if __name__ == "__main__":
    main()
