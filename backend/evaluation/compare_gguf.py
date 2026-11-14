"""Local compact-runtime comparison. Start the pinned llama-server on port 8081 first."""

import base64
import hashlib
import io
import json
import math
import sys
import time
from pathlib import Path

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.detectors.smaug_runtime import image_views


def main():
    head = json.loads((ROOT / "models/smaug-gguf/head.json").read_text())
    rows = []
    with httpx.Client(base_url="http://127.0.0.1:8081", timeout=180) as client:
        props = client.get("/props")
        props.raise_for_status()
        marker = props.json()["media_marker"]
        samples = json.loads((ROOT / "evaluation/smaug-comparison.json").read_text())["rows"]
        for sample in samples:
            path = ROOT / "evaluation/samples" / sample["file"]
            with Image.open(path) as source:
                original = source.convert("RGB")
            buffer = io.BytesIO()
            original.save(buffer, format="JPEG", quality=85)
            with Image.open(io.BytesIO(buffer.getvalue())) as jpeg:
                variants = [
                    ("original", original),
                    ("jpeg-85", jpeg.convert("RGB")),
                    ("resize-128", original.resize((128, 128))),
                ]
            scores, seconds = {}, {}
            for name, picture in variants:
                started = time.monotonic()
                logits = []
                for crop in image_views(picture):
                    image_bytes = io.BytesIO()
                    crop.save(image_bytes, format="PNG")
                    response = client.post(
                        "/embeddings",
                        json={
                            "content": {
                                "prompt_string": marker,
                                "multimodal_data": [
                                    base64.b64encode(image_bytes.getvalue()).decode()
                                ],
                            },
                            "embd_normalize": 2,
                        },
                    )
                    response.raise_for_status()
                    vector = response.json()[0]["embedding"]
                    if isinstance(vector[0], list):
                        vector = vector[0]
                    assert len(vector) == len(head["weight"]) == 768
                    assert all(math.isfinite(value) for value in vector)
                    logits.append(sum(w * x for w, x in zip(head["weight"], vector)) + head["bias"])
                scores[name] = 1 / (1 + math.exp(-sum(logits) / len(logits)))
                seconds[name] = round(time.monotonic() - started, 2)
                print(sample["file"], name, scores[name], seconds[name], flush=True)
            rows.append(
                {
                    "file": sample["file"],
                    "expected_ai": sample["expected_ai"],
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "scores": scores,
                    "seconds": seconds,
                }
            )
            (ROOT / "evaluation/gguf-comparison.json").write_text(
                json.dumps(
                    {
                        "model_id": "abacusai/Smaug-AI-Image-Detector-GGUF",
                        "revision": "cfb5e8649729d05a710c67ac8f4a0c2bf44b5824",
                        "runtime": "llama.cpp b12359, Q8_0 encoder and projector, one CPU thread, Windows",
                        "warning": "Development comparison, not an independent accuracy benchmark or a Vercel deployment test.",
                        "rows": rows,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )


if __name__ == "__main__":
    main()
