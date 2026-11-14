"""Local development comparison; not a held-out benchmark. Run with .venv Python."""

import os

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
import hashlib
import io
import json
import sys
import time
from pathlib import Path

import torch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.detectors.image_model import ImageDetector

torch.set_num_threads(4)
print("Loading candidate on CPU", flush=True)
detector = ImageDetector()
detector.load()
if not detector.ready:
    raise RuntimeError(detector.message)
rows = []
samples = [
    ("user-building.png", 1),
    ("astronaut.png", 0),
    ("camera.png", 0),
    ("chelsea.png", 0),
    ("text2img-1.png", 1),
    ("sdxl-text2img.png", 1),
    ("text2img-vader.png", 1),
]
for name, label in samples:
    source = ROOT / "evaluation" / "samples" / name
    with Image.open(source) as original:
        image = original.convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    with Image.open(io.BytesIO(buffer.getvalue())) as jpeg:
        variants = [
            ("original", image),
            ("jpeg-85", jpeg.convert("RGB")),
            ("resize-128", image.resize((128, 128))),
        ]
    scores = {}
    for variant, picture in variants:
        start = time.monotonic()
        scores[variant], _ = detector.model.predict(picture)
        print(name, variant, scores[variant], f"{time.monotonic() - start:.1f}s", flush=True)
    rows.append(
        {
            "file": name,
            "expected_ai": label,
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "scores": scores,
        }
    )
    (ROOT / "evaluation" / "smaug-comparison.json").write_text(
        json.dumps(
            {
                "model_id": "abacusai/Smaug-AI-Image-Detector",
                "revision": (ROOT / "models" / "smaug" / "revision.txt").read_text(),
                "warning": "Development smoke comparison, including the user-reported AI image. Not an independent benchmark; no threshold fitted.",
                "rows": rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
