from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.schemas import AnalysisReport, HealthResponse
from app.services.analysis import AnalysisService

analysis_service = AnalysisService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_in_threadpool(analysis_service.detector.load)
    try:
        yield
    finally:
        await run_in_threadpool(analysis_service.detector.close)


app = FastAPI(
    lifespan=lifespan,
    title=settings.app_name,
    version=settings.version,
    description="Explainable media verification and deepfake-triage API",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/api/v1/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.version,
        neural_detector="ready" if analysis_service.detector.ready else "unavailable",
        detector_message=analysis_service.detector.message,
    )


@app.post("/api/v1/analyze", response_model=AnalysisReport, tags=["analysis"])
async def analyze_media(file: Annotated[UploadFile, File()]) -> AnalysisReport:
    filename = file.filename or "unnamed-media"
    content = await file.read(settings.max_upload_bytes + 1)
    await file.close()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty."
        )
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB limit.",
        )
    try:
        report = await analysis_service.analyze(content, filename, file.content_type)
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(
            status_code=413, detail="This image has too many pixels to process safely."
        ) from None
    if any(item.id == "decode-failure" for item in report.evidence):
        raise HTTPException(
            status_code=400, detail="This image is damaged or couldn't be read. Try another file."
        )
    if report.media.media_kind == "unknown":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file. Upload a recognized image, video, or audio file.",
        )
    return report
