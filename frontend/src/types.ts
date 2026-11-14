export type MediaKind = "image" | "video" | "audio" | "unknown";
export type Severity = "info" | "low" | "medium" | "high";
export type Verdict = "low-risk" | "review" | "suspicious" | "inconclusive";

export interface MediaMetadata {
  filename: string;
  media_kind: MediaKind;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  extension: string;
  dimensions: string | null;
  format: string | null;
  color_mode: string | null;
  created_at: string | null;
  software: string | null;
}

export interface Evidence {
  id: string;
  title: string;
  description: string;
  severity: Severity;
  score: number;
  category: "integrity" | "metadata" | "visual" | "model" | "provenance";
  observed: string | null;
}

export interface AnalysisReport {
  analysis_id: string;
  analyzed_at: string;
  verdict: Verdict;
  risk_score: number | null;
  confidence: number | null;
  spatial_analysis?: SpatialAnalysis | null;
  detection: {
    status: "complete" | "unavailable" | "unsupported" | "failed";
    ai_score: number | null;
    model_id: string | null;
    revision: string | null;
    message: string;
    calibrated: boolean;
    stability: "not-tested" | "consistent" | "sensitive";
    check_scores: Record<string, number>;
    scope: string;
  };
  summary: string;
  media: MediaMetadata;
  evidence: Evidence[];
  limitations: {
    neural_detector_available: boolean;
    provenance_manifest_found: boolean;
    notes: string[];
  };
  processing_ms: number;
  engine_version: string;
}

export interface SpatialMetric {
  id: string;
  name: string;
  value: number;
  unit: string;
  value_label: string;
  minimum: number;
  maximum: number;
  median: number;
  cells: number[];
  summary: string;
  method: string;
  limitation: string;
}

export interface SpatialAnalysis {
  status: "complete" | "unsupported" | "failed";
  message: string;
  version: string;
  width: number;
  height: number;
  rows: number;
  columns: number;
  preview_data_url: string | null;
  metrics: SpatialMetric[];
}
