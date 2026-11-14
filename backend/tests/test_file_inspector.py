import io

from PIL import Image

from app.services.file_inspector import detect_signature, inspect_file


def png_bytes() -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (32, 32), color=(30, 60, 90)).save(stream, format="PNG")
    return stream.getvalue()


def test_detects_png_by_signature() -> None:
    mime, kind = detect_signature(png_bytes(), "sample.bin")
    assert mime == "image/png"
    assert kind == "image"


def test_inspection_builds_stable_sha256() -> None:
    content = png_bytes()
    first = inspect_file(content, "sample.png", "image/png")
    second = inspect_file(content, "renamed.png", "image/png")
    assert first.metadata.sha256 == second.metadata.sha256
    assert first.metadata.dimensions == "32 × 32"


def test_mime_mismatch_is_reported() -> None:
    result = inspect_file(png_bytes(), "sample.png", "audio/mpeg")
    assert any(item.id == "mime-mismatch" for item in result.evidence)
