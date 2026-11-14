import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit


def allowed_origins() -> tuple[str, ...]:
    raw = os.environ.get(
        "VERISIGHT_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    )
    origins = tuple(value.strip().rstrip("/") for value in raw.split(",") if value.strip())
    for origin in origins:
        url = urlsplit(origin)
        if (
            url.scheme not in {"http", "https"} or not url.hostname or url.path
            or url.query or url.fragment or url.username or url.password
        ):
            raise ValueError("VERISIGHT_ALLOWED_ORIGINS must contain comma-separated HTTP(S) origins")
    return origins


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "VeriSight API"
    version: str = "0.1.0"
    max_upload_bytes: int = 100 * 1024 * 1024
    allowed_origins: tuple[str, ...] = field(default_factory=allowed_origins)


settings = Settings()
