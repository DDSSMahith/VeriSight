from __future__ import annotations

import hashlib
import io
import math
import mimetypes
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import ExifTags, Image, UnidentifiedImageError

from app.schemas import Evidence, MediaKind, MediaMetadata

MAGIC_SIGNATURES: tuple[tuple[bytes, str, MediaKind], ...] = (
    (b"\xff\xd8\xff", "image/jpeg", "image"),
    (b"\x89PNG\r\n\x1a\n", "image/png", "image"),
    (b"GIF87a", "image/gif", "image"),
    (b"GIF89a", "image/gif", "image"),
    (b"RIFF", "application/riff", "unknown"),
    (b"ID3", "audio/mpeg", "audio"),
    (b"OggS", "application/ogg", "audio"),
    (b"fLaC", "audio/flac", "audio"),
    (b"\x1aE\xdf\xa3", "video/webm", "video"),
)

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"}


@dataclass(slots=True)
class InspectionResult:
    metadata: MediaMetadata
    evidence: list[Evidence]
    provenance_found: bool


def _classify_by_extension(extension: str) -> MediaKind:
    if extension in IMAGE_EXTENSIONS:
        return "image"
    if extension in VIDEO_EXTENSIONS:
        return "video"
    if extension in AUDIO_EXTENSIONS:
        return "audio"
    return "unknown"


def detect_signature(content: bytes, filename: str) -> tuple[str, MediaKind]:
    extension = Path(filename).suffix.lower()
    if len(content) >= 12 and content[4:8] == b"ftyp":
        return (
            "video/mp4" if extension in VIDEO_EXTENSIONS else "audio/mp4",
            _classify_by_extension(extension),
        )
    if content.startswith(b"RIFF") and len(content) >= 12:
        subtype = content[8:12]
        if subtype == b"WAVE":
            return "audio/wav", "audio"
        if subtype == b"AVI ":
            return "video/x-msvideo", "video"
        if subtype == b"WEBP":
            return "image/webp", "image"
    for signature, mime, kind in MAGIC_SIGNATURES:
        if content.startswith(signature):
            return mime, kind
    guessed_mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return guessed_mime, _classify_by_extension(extension)


def _shannon_entropy(content: bytes, sample_size: int = 1_000_000) -> float:
    sample = content[:sample_size]
    if not sample:
        return 0.0
    counts = Counter(sample)
    length = len(sample)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def _metadata_evidence(exif: dict[str, Any]) -> tuple[list[Evidence], str | None, str | None]:
    evidence: list[Evidence] = []
    software = str(exif.get("Software", "")).strip() or None
    created_at = str(exif.get("DateTimeOriginal", exif.get("DateTime", ""))).strip() or None
    if software:
        lowered = software.lower()
        generator_tokens = ("stable diffusion", "midjourney", "dall-e", "comfyui", "automatic1111")
        editor_tokens = ("photoshop", "gimp", "lightroom", "affinity")
        if any(token in lowered for token in generator_tokens):
            evidence.append(
                Evidence(
                    id="generator-software",
                    title="Generative software marker",
                    description="The embedded software field names a known generative-media tool.",
                    severity="high",
                    score=0.92,
                    category="metadata",
                    observed=software,
                )
            )
        elif any(token in lowered for token in editor_tokens):
            evidence.append(
                Evidence(
                    id="editing-software",
                    title="Editing software marker",
                    description="The media was exported by editing software. Editing alone does not imply deception.",
                    severity="low",
                    score=0.28,
                    category="metadata",
                    observed=software,
                )
            )
    else:
        evidence.append(
            Evidence(
                id="metadata-absent",
                title="Sparse origin metadata",
                description="No camera or software origin fields were found. Many platforms strip this data, so this is weak evidence.",
                severity="info",
                score=0.12,
                category="metadata",
                observed="No software/date field",
            )
        )
    return evidence, software, created_at


def _image_forensics(content: bytes) -> tuple[dict[str, Any], list[Evidence]]:
    evidence: list[Evidence] = []
    details: dict[str, Any] = {}
    try:
        with Image.open(io.BytesIO(content)) as image:
            image.verify()
        with Image.open(io.BytesIO(content)) as image:
            details.update(
                format=image.format,
                dimensions=f"{image.width} × {image.height}",
                color_mode=image.mode,
            )
            raw_exif = image.getexif()
            exif = {ExifTags.TAGS.get(key, str(key)): value for key, value in raw_exif.items()}
            metadata_evidence, software, created_at = _metadata_evidence(exif)
            evidence.extend(metadata_evidence)
            details.update(software=software, created_at=created_at)

            grayscale = np.asarray(
                image.convert("L").resize((min(image.width, 512), min(image.height, 512))),
                dtype=np.float32,
            )
            if min(grayscale.shape) >= 2:
                horizontal = np.abs(np.diff(grayscale, axis=1))
                vertical = np.abs(np.diff(grayscale, axis=0))
                edge_mean = float((horizontal.mean() + vertical.mean()) / 2)
                edge_std = float((horizontal.std() + vertical.std()) / 2)
                details["edge_mean"] = round(edge_mean, 2)
                if edge_mean < 1.2 and image.width * image.height > 250_000:
                    evidence.append(
                        Evidence(
                            id="low-texture-uniformity",
                            title="Unusually uniform texture",
                            description="Large regions contain very little local variation. This can occur after denoising, generation, or heavy compression.",
                            severity="low",
                            score=0.33,
                            category="visual",
                            observed=f"Mean edge energy {edge_mean:.2f}",
                        )
                    )
                if edge_std > 65:
                    evidence.append(
                        Evidence(
                            id="edge-discontinuity",
                            title="Strong edge discontinuities",
                            description="The image contains abrupt local transitions. Compositing is one possible cause, but graphics and text can produce the same pattern.",
                            severity="low",
                            score=0.31,
                            category="visual",
                            observed=f"Edge deviation {edge_std:.1f}",
                        )
                    )

            if image.format == "JPEG":
                end_marker = content.rfind(b"\xff\xd9")
                trailing = max(0, len(content) - (end_marker + 2)) if end_marker >= 0 else 0
                if trailing > 128:
                    evidence.append(
                        Evidence(
                            id="trailing-payload",
                            title="Data after image end marker",
                            description="The JPEG contains an appended payload after its normal end marker.",
                            severity="medium",
                            score=0.62,
                            category="integrity",
                            observed=f"{trailing:,} trailing bytes",
                        )
                    )
    except (UnidentifiedImageError, OSError, ValueError):
        evidence.append(
            Evidence(
                id="decode-failure",
                title="Image decode failed",
                description="The file signature indicates an image, but a strict decoder could not validate it.",
                severity="high",
                score=0.82,
                category="integrity",
                observed="Invalid or damaged image stream",
            )
        )
    return details, evidence


def inspect_file(content: bytes, filename: str, declared_mime: str | None) -> InspectionResult:
    extension = Path(filename).suffix.lower()
    detected_mime, media_kind = detect_signature(content, filename)
    evidence: list[Evidence] = []
    declared = declared_mime or "application/octet-stream"

    if (
        declared != "application/octet-stream"
        and declared.split("/")[0] != detected_mime.split("/")[0]
    ):
        evidence.append(
            Evidence(
                id="mime-mismatch",
                title="File type mismatch",
                description="The uploaded MIME type does not agree with the file's binary signature.",
                severity="medium",
                score=0.68,
                category="integrity",
                observed=f"Declared {declared}; detected {detected_mime}",
            )
        )

    entropy = _shannon_entropy(content)
    evidence.append(
        Evidence(
            id="cryptographic-identity",
            title="Evidence identity established",
            description="A SHA-256 digest was calculated so this exact file can be referenced and compared later.",
            severity="info",
            score=0.0,
            category="integrity",
            observed=hashlib.sha256(content).hexdigest()[:20] + "…",
        )
    )
    if entropy > 7.97:
        evidence.append(
            Evidence(
                id="high-entropy",
                title="Near-random byte distribution",
                description="The file has unusually high byte entropy, which may indicate encryption, packing, or a mislabeled container.",
                severity="low",
                score=0.30,
                category="integrity",
                observed=f"{entropy:.3f} bits/byte",
            )
        )

    details: dict[str, Any] = {}
    if media_kind == "image":
        details, image_evidence = _image_forensics(content)
        evidence.extend(image_evidence)
    else:
        evidence.append(
            Evidence(
                id="container-only-analysis",
                title="Container-level analysis",
                description="This build validates the file container and metadata; a specialist temporal or acoustic model is not configured.",
                severity="info",
                score=0.0,
                category="model",
                observed=f"{media_kind.title()} specialist unavailable",
            )
        )

    provenance_found = (
        b"c2pa" in content[:2_000_000].lower() or b"contentauth" in content[:2_000_000].lower()
    )
    evidence.append(
        Evidence(
            id="provenance-manifest" if provenance_found else "provenance-unavailable",
            title="Provenance marker found"
            if provenance_found
            else "No provenance manifest detected",
            description=(
                "The container includes a marker associated with content provenance; cryptographic manifest validation should follow."
                if provenance_found
                else "No C2PA-style marker was found in the scanned container. Absence is not evidence of manipulation."
            ),
            severity="info",
            score=0.0,
            category="provenance",
            observed="Marker present" if provenance_found else "Not present",
        )
    )

    metadata = MediaMetadata(
        filename=filename,
        media_kind=media_kind,
        mime_type=detected_mime,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        extension=extension or "none",
        dimensions=details.get("dimensions"),
        format=details.get("format"),
        color_mode=details.get("color_mode"),
        created_at=details.get("created_at"),
        software=details.get("software"),
    )
    return InspectionResult(metadata=metadata, evidence=evidence, provenance_found=provenance_found)
