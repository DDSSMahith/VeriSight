import type { AnalysisReport } from "./types";

type Detection = AnalysisReport["detection"];
export function formatModelScore(score: number): string {
  if (score > 0 && score < 0.0001) return "<0.01";
  if (score < 1 && score > 0.9999) return ">99.99";
  return (score * 100).toFixed(2);
}
const validScore = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1;
const preference = (score: number) => score > 0.5 ? "AI-generated" : score < 0.5 ? "human-made" : "neither class";

/** Describe classifier outputs, without converting them into authenticity verdicts. */
export function presentModel(detection: Detection) {
  const score = detection.ai_score;
  if (detection.status !== "complete" || !validScore(score)) {
    return {
      title: detection.status === "unsupported" ? "This file needs a different detector" : "No model result",
      description: detection.message,
      recheckTitle: "Not run",
      recheckDescription: "There are no model outputs to compare for this file.",
      checks: [],
    };
  }
  const names: Record<string, string> = { original: "Original image", "jpeg-85": "JPEG copy", "resize-128": "Smaller copy" };
  const values = { ...detection.check_scores, original: score };
  const checks = Object.entries(values).filter(([, value]) => validScore(value)).map(([key, value]) => ({
    key, name: names[key] ?? key, value, preference: preference(value),
  })).sort((a, b) => a.key === "original" ? -1 : b.key === "original" ? 1 : 0);
  const hasRechecks = checks.length > 1;
  const disagrees = new Set(checks.map(check => check.preference)).size > 1;
  const range = Math.max(...checks.map(check => check.value)) - Math.min(...checks.map(check => check.value));
  const sensitive = detection.stability === "sensitive" || range >= 0.6;
  return {
    title: score === 0.5 ? "No model preference" : `Model favors ${preference(score)}`,
    description: score === 0.5
      ? "The two classes received equal output on the original image."
      : `On the original image, the classifier gave its ${preference(score)} class the higher output. This describes the model’s response, not a verified real/fake result.`,
    recheckTitle: !hasRechecks ? "Not run" : disagrees ? "Re-checks disagree" : sensitive ? "Large score changes" : "Same model preference",
    recheckDescription: !hasRechecks ? "Only the original image was scored."
      : disagrees ? "Resizing or compression changed which class the model favored. Treat this image’s result with particular caution."
      : sensitive ? "The preferred class stayed the same, but the output changed sharply after resizing or compression."
      : "The tested copies favored the same class. Agreement across these copies does not establish accuracy.",
    checks,
  };
}
