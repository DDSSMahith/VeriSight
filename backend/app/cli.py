"""Command-line entry point for the VeriSight API."""

import uvicorn


def main() -> None:
    """Start the local API."""
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
    )


if __name__ == "__main__":
    main()
