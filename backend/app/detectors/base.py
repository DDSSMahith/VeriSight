from dataclasses import dataclass
from typing import Protocol

from app.schemas import MediaKind


@dataclass(frozen=True, slots=True)
class DetectorSignal:
    detector_id: str
    label: str
    synthetic_probability: float
    confidence: float
    explanation: str


class DetectorAdapter(Protocol):
    """Boundary for benchmarked neural detectors.

    Adapters should own preprocessing, inference, and calibration. Probabilities must
    be calibrated against a held-out distribution rather than exposed as raw logits.
    """

    name: str
    supported_kinds: frozenset[MediaKind]

    async def analyze(self, content: bytes, mime_type: str) -> list[DetectorSignal]: ...
