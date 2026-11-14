import math

import pytest
from PIL import Image

from app.detectors import smaug_gguf_runtime


def test_compact_runtime_uses_mean_logits(monkeypatch):
    class Response:
        def __init__(self, value):
            self.value = value

        def raise_for_status(self):
            return None

        def json(self):
            return [{"embedding": [self.value] + [0.0] * 767}]

    class Client:
        def __init__(self):
            self.values = iter([-4.0, 1.0, 1.0])

        def post(self, path, json):
            assert path == "/embeddings"
            assert json["embd_normalize"] == 2
            return Response(next(self.values))

    runtime = smaug_gguf_runtime.SmaugGGUFRuntime.__new__(
        smaug_gguf_runtime.SmaugGGUFRuntime
    )
    runtime.weights = [1.0] + [0.0] * 767
    runtime.bias = 0.0
    runtime.marker = "marker"
    runtime.client = Client()
    monkeypatch.setattr(
        smaug_gguf_runtime,
        "image_views",
        lambda image: [Image.new("RGB", (8, 8)) for _ in range(3)],
    )

    score, crops = runtime.predict(Image.new("RGB", (64, 64)))
    assert score == pytest.approx(1 / (1 + math.exp(2 / 3)))
    assert score < 0.5
    assert crops[0] < crops[1] == crops[2]
