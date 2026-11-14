from typing import Literal

from pydantic import BaseModel, Field

MediaKind = Literal["image", "video", "audio", "unknown"]
Severity = Literal["info", "low", "medium", "high"]
Verdict = Literal["low-risk", "review", "suspicious", "inconclusive"]


class MediaMetadata(BaseModel):
    filename: str
    media_kind: MediaKind
    mime_type: str
    size_bytes: int
    sha256: str
    extension: str
    dimensions: str | None = None
    format: str | None = None
    color_mode: str | None = None
    created_at: str | None = None
    software: str | None = None


class Evidence(BaseModel):
    id: str
    title: str
    description: str
    severity: Severity
    score: float = Field(ge=0, le=1)
    category: Literal["integrity", "metadata", "visual", "model", "provenance"]
    observed: str | None = None


class AnalysisLimitations(BaseModel):
    neural_detector_available: bool
    provenance_manifest_found: bool
    notes: list[str]


class SpatialMetric(BaseModel):
    id: str
    name: str
    value: float
    unit: str
    value_label: str
    minimum: float
    maximum: float
    median: float
    cells: list[float]
    summary: str
    method: str
    limitation: str


class SpatialAnalysis(BaseModel):
    status: Literal["complete", "unsupported", "failed"]
    message: str
    version: str = "spatial-v1"
    width: int = 0
    height: int = 0
    rows: int = 0
    columns: int = 0
    preview_data_url: str | None = None
    metrics: list[SpatialMetric] = Field(default_factory=list)


class AnalysisReport(BaseModel):
    analysis_id: str
    analyzed_at: str
    verdict: Verdict
    risk_score: float | None = Field(default=None, ge=0, le=100)
    confidence: float | None = None
    detection: "DetectionResult"
    spatial_analysis: SpatialAnalysis | None = None
    summary: str
    media: MediaMetadata
    evidence: list[Evidence]
    limitations: AnalysisLimitations
    processing_ms: int
    engine_version: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    neural_detector: Literal["unavailable", "ready"]
    detector_message: str


class DetectionResult(BaseModel):
    status: Literal["complete", "unavailable", "unsupported", "failed"]
    model_id: str | None = None
    revision: str | None = None
    ai_score: float | None = Field(default=None, ge=0, le=1)
    message: str
    calibrated: bool = False
    stability: Literal["not-tested", "consistent", "sensitive"] = "not-tested"
    check_scores: dict[str, float] = Field(default_factory=dict)
    crop_scores: list[float] = Field(default_factory=list)
    method: str | None = None
    scope: str = "AI-generated images; not face swaps, video, or audio"
