import type { AnalysisReport } from "./types";

export const API_BASE_URL = (import.meta.env?.VITE_API_BASE_URL ?? "").trim().replace(/\/+$/, "");
const hosted = import.meta.env?.PROD === true;
export const API_DOCS_URL = `${API_BASE_URL || (hosted ? "" : "http://127.0.0.1:8000")}/api/docs`;

export function apiUrl(path: string, base = API_BASE_URL): string {
  return `${base.trim().replace(/\/+$/, "")}${path}`;
}

export class ApiError extends Error {
  public readonly status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const connectionHelp = hosted
  ? "We couldn’t reach the analysis service. It may be starting up or temporarily unavailable. Please try again shortly."
  : "We couldn’t reach the backend. In a terminal, run ‘cd backend’ then ‘npm run dev’, and keep it open. Wait for ‘Application startup complete’, then retry.";
const addressHelp = hosted
  ? "The analysis service isn’t connected to this website yet. Its backend address needs to be configured."
  : "This page isn’t connected to the API. Open http://localhost:5173 with both development servers running, then try again.";

async function apiRequest(url: string, options: RequestInit, timeoutMs: number): Promise<unknown> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(apiUrl(url), { ...options, signal: controller.signal });
    if ([502, 503, 504].includes(response.status)) throw new ApiError(connectionHelp, response.status);
    const isJson = response.headers.get("content-type")?.includes("application/json");
    if (!isJson) {
      throw new ApiError(response.status >= 500 ? connectionHelp : addressHelp, response.status);
    }
    const body = await response.json();
    if (!response.ok) {
      throw new ApiError(typeof body?.detail === "string" ? body.detail : "The check couldn’t finish. Please try again.", response.status);
    }
    return body;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (controller.signal.aborted) {
      throw new ApiError("The image check took too long. Please wait a moment, then retry. Keep the original image: shrinking it can make detection less reliable.", 408);
    }
    throw new ApiError(connectionHelp, 0);
  } finally {
    clearTimeout(timeout);
  }
}

export async function checkBackend(): Promise<string> {
  const health = await apiRequest("/api/v1/health", { cache: "no-store" }, 5000) as {
    status?: string; service?: string; neural_detector?: string;
  };
  if (health?.status !== "ok" || health.service !== "VeriSight API") throw new ApiError(addressHelp, 502);
  if (!health.neural_detector) throw new ApiError(hosted ? "The analysis service needs an update before it can check images." : "An older backend is running. Stop it with Ctrl+C, then run npm run dev from the backend folder.", 409);
  return health.neural_detector === "ready"
    ? "Backend connected · Experimental image model loaded (accuracy not validated)"
    : hosted ? "Analysis service connected · The image detector is temporarily unavailable."
    : "Backend connected · Image model unavailable. Run setup-model.cmd from the project root, then restart the backend.";
}

export async function analyzeMedia(file: File): Promise<AnalysisReport> {
  await checkBackend();
  const data = new FormData();
  data.append("file", file);
  const report = await apiRequest("/api/v1/analyze", { method: "POST", body: data }, 290000) as AnalysisReport;
  if (!report?.detection) {
    throw new ApiError(hosted ? "The analysis service needs an update before it can check images." : "An older backend is still running. Stop it with Ctrl+C, then run npm run dev from the backend folder and retry.", 409);
  }
  return report;
}
