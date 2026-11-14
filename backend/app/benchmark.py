"""Evaluate labeled local files without fitting or enabling a decision threshold.

CSV columns: path,label,group,task. Labels: real/fake. Tasks: ai-generation/face-manipulation.
Paths are relative to the CSV. Use independent data, not training or tuning examples.
"""

import argparse
import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from app.detectors.image_model import MODEL_ID, REVISION, ImageDetector


def load_manifest(path: Path) -> list[dict]:
    rows = []
    seen = set()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"path", "label", "group", "task"}.issubset(reader.fieldnames or []):
            raise ValueError("CSV requires path,label,group,task columns")
        for line, row in enumerate(reader, 2):
            if row["label"] not in {"real", "fake"}:
                raise ValueError(f"Line {line}: label must be real or fake")
            if row["task"] not in {"ai-generation", "face-manipulation"} or not row["group"]:
                raise ValueError(f"Line {line}: task and group must be specified")
            source = (path.parent / row["path"]).resolve()
            key = (str(source).lower(), row["task"])
            if key in seen:
                raise ValueError(f"Line {line}: duplicate file in the same task")
            seen.add(key)
            rows.append({**row, "path": str(source)})
    if not rows:
        raise ValueError("Manifest contains no samples")
    return rows


def summarize(rows: list[dict]) -> dict:
    completed = [r for r in rows if r["status"] == "complete"]
    real = [r for r in completed if r["label"] == "real"]
    fake = [r for r in completed if r["label"] == "fake"]
    fp = sum(r["ai_score"] >= 0.5 for r in real)
    fn = sum(r["ai_score"] < 0.5 for r in fake)
    return {
        "total": len(rows),
        "scored": len(completed),
        "failed": sum(r["status"] == "failed" for r in rows),
        "unsupported": sum(r["status"] == "unsupported" for r in rows),
        "score_coverage": len(completed) / len(rows) if rows else 0,
        "real_scored": len(real),
        "fake_scored": len(fake),
        "diagnostic_threshold": 0.5,
        "false_positives": fp,
        "false_negatives": fn,
        "false_positive_rate": fp / len(real) if real else None,
        "false_negative_rate": fn / len(fake) if fake else None,
        "balanced_accuracy": 1 - (fp / len(real) + fn / len(fake)) / 2 if real and fake else None,
        "extreme_score_count": sum(
            r["ai_score"] <= 0.01 or r["ai_score"] >= 0.99 for r in completed
        ),
        "unstable_count": sum(r.get("stability") == "sensitive" for r in completed),
        "authenticity_verdict_coverage": 0,
    }


def evaluate(rows: list[dict], detector: ImageDetector) -> dict:
    results = []
    seen_hashes = set()
    for row in rows:
        result = dict(row)
        try:
            data = Path(row["path"]).read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            result["sha256"] = digest
            key = (digest, row["task"])
            if key in seen_hashes:
                raise ValueError("Duplicate image bytes in the same task; excluded from metrics")
            seen_hashes.add(key)
            if row["task"] == "face-manipulation":
                result.update(
                    status="unsupported", message="No face-manipulation detector installed"
                )
            else:
                detection = detector.analyze(data, "image")
                result.update(detection.model_dump())
                if detection.status == "unavailable":
                    result["status"] = "failed"
        except (OSError, ValueError, RuntimeError) as error:
            result.update(status="failed", message=str(error))
        results.append(result)
    groups = {}
    for row in results:
        key = f"{row['task']}/{row['group']}"
        groups.setdefault(key, []).append(row)
    return {
        "evaluated_at": datetime.now(UTC).isoformat(),
        "model_id": MODEL_ID,
        "revision": REVISION,
        "warning": "Diagnostic evaluation only. Data independence and labels must be audited. "
        "Metrics exclude unscored files; see coverage and errors. Face manipulation is unsupported. "
        "The fixed 0.5 diagnostic threshold is not an approved product decision rule. "
        "This run does not calibrate the model or enable authenticity verdicts.",
        "summary": summarize(results),
        "groups": {name: summarize(items) for name, items in groups.items()},
        "rows": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = load_manifest(args.manifest)
    detector = ImageDetector()
    detector.load()
    if not detector.ready:
        raise RuntimeError(detector.message)
    report = evaluate(rows, detector)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"summary": report["summary"], "groups": report["groups"]}, indent=2))


if __name__ == "__main__":
    main()
