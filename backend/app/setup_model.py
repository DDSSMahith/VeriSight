"""Explicit download step; uploads never trigger network requests."""

import hashlib
import json
import os

import httpx

from app.detectors.image_model import MODEL_DIR, MODEL_ID, REVISION
from app.detectors.model_manifest import FILES


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    hashes = {}
    with httpx.Client(follow_redirects=True, timeout=120) as client:
        for name, expected in FILES.items():
            target = MODEL_DIR / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                with target.open("rb") as source:
                    if hashlib.file_digest(source, "sha256").hexdigest() == expected:
                        hashes[name] = expected
                        print(f"Verified {name}", flush=True)
                        continue
            temp = target.with_suffix(target.suffix + ".part")
            print(f"Downloading {name}...", flush=True)
            digest = hashlib.sha256()
            with client.stream(
                "GET", f"https://huggingface.co/{MODEL_ID}/resolve/{REVISION}/{name}"
            ) as response:
                response.raise_for_status()
                with temp.open("wb") as output:
                    for chunk in response.iter_bytes(1024 * 1024):
                        output.write(chunk)
                        digest.update(chunk)
            if digest.hexdigest() != expected:
                raise ValueError(f"Checksum mismatch for {name}")
            os.replace(temp, target)
            hashes[name] = digest.hexdigest()
    (MODEL_DIR / "revision.txt").write_text(REVISION, encoding="utf-8")
    (MODEL_DIR / "checksums.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    print("Model downloaded and verified. Run cd backend, then npm run dev from the project root.")


if __name__ == "__main__":
    main()
