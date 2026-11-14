"""Compact local Smaug inference through a loopback-only llama.cpp process."""

import base64
import io
import json
import math
import os
import subprocess
import time
from pathlib import Path

import httpx
from PIL import Image

from app.detectors.smaug_runtime import image_views


class SmaugGGUFRuntime:
    def __init__(self, model_dir: Path, server_binary: Path | None = None):
        binary = server_binary or Path(
            os.environ.get("VERISIGHT_LLAMA_SERVER", "/opt/llama/llama-server")
        )
        if not binary.is_file():
            raise FileNotFoundError(f"Compact model runtime not found: {binary}")

        head = json.loads((model_dir / "head.json").read_text(encoding="utf-8"))
        self.weights = [float(value) for value in head["weight"]]
        self.bias = float(head["bias"])
        if len(self.weights) != 768 or not all(
            math.isfinite(value) for value in [*self.weights, self.bias]
        ):
            raise ValueError("Invalid compact model classification head")

        port = int(os.environ.get("VERISIGHT_LLAMA_PORT", "8081"))
        if not 1024 <= port <= 65535:
            raise ValueError("VERISIGHT_LLAMA_PORT must be between 1024 and 65535")
        self.url = f"http://127.0.0.1:{port}"
        threads = max(1, min(int(os.environ.get("VERISIGHT_MODEL_THREADS", "1")), 4))
        self.process = subprocess.Popen(
            [
                str(binary),
                "-m",
                str(model_dir / "Smaug-AI-Image-Detector-Q8_0.gguf"),
                "--mmproj",
                str(model_dir / "mmproj-Smaug-AI-Image-Detector-Q8_0.gguf"),
                "--embeddings",
                "--pooling",
                "mean",
                "--image-max-tokens",
                "140",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--threads",
                str(threads),
                "--threads-batch",
                str(threads),
                "--parallel",
                "1",
                "--ctx-size",
                "512",
                "--no-webui",
            ],
            stdin=subprocess.DEVNULL,
        )
        self.client = httpx.Client(base_url=self.url, timeout=240)
        try:
            self.marker = self._wait_until_ready()
        except Exception:
            self.close()
            raise

    def _wait_until_ready(self) -> str:
        deadline = time.monotonic() + 60
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(
                    f"Compact model process exited during startup ({self.process.returncode})"
                )
            try:
                response = self.client.get("/props")
                response.raise_for_status()
                marker = response.json().get("media_marker")
                if isinstance(marker, str) and marker:
                    return marker
            except (httpx.HTTPError, ValueError) as error:
                last_error = error
            time.sleep(0.2)
        raise RuntimeError("Compact model process did not become ready") from last_error

    def _logit(self, crop: Image.Image) -> float:
        buffer = io.BytesIO()
        crop.save(buffer, format="PNG")
        response = self.client.post(
            "/embeddings",
            json={
                "content": {
                    "prompt_string": self.marker,
                    "multimodal_data": [base64.b64encode(buffer.getvalue()).decode("ascii")],
                },
                "embd_normalize": 2,
            },
        )
        response.raise_for_status()
        vector = response.json()[0]["embedding"]
        if vector and isinstance(vector[0], list):
            vector = vector[0]
        if len(vector) != len(self.weights) or not all(math.isfinite(value) for value in vector):
            raise ValueError("Invalid compact model embedding")
        return sum(
            weight * value for weight, value in zip(self.weights, vector, strict=True)
        ) + self.bias

    def predict(self, image: Image.Image) -> tuple[float, list[float]]:
        logits = [self._logit(crop) for crop in image_views(image)]
        crop_scores = [1 / (1 + math.exp(-logit)) for logit in logits]
        score = 1 / (1 + math.exp(-sum(logits) / len(logits)))
        return score, crop_scores

    def close(self) -> None:
        self.client.close()
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
