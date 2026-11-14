import pytest

from app.config import Settings


def test_local_origins_are_default(monkeypatch):
    monkeypatch.delenv("VERISIGHT_ALLOWED_ORIGINS", raising=False)
    assert Settings().allowed_origins == ("http://localhost:5173", "http://127.0.0.1:5173")


def test_explicit_hosted_origins_replace_local_defaults(monkeypatch):
    monkeypatch.setenv(
        "VERISIGHT_ALLOWED_ORIGINS", "https://verisight.example/, https://preview.example"
    )
    assert Settings().allowed_origins == (
        "https://verisight.example", "https://preview.example"
    )


@pytest.mark.parametrize("origin", ["*", "https://example.com/path", "ftp://example.com"])
def test_bad_origin_configuration_fails_clearly(monkeypatch, origin):
    monkeypatch.setenv("VERISIGHT_ALLOWED_ORIGINS", origin)
    with pytest.raises(ValueError, match="HTTP"):
        Settings()
