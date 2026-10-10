"""File helpers kept inside the standalone ingestion-data package."""

import hashlib
import json
from pathlib import Path


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fresh_directory(path):
    path = Path(path).resolve()
    if any(part.upper() == "ANSWERS" for part in path.parts):
        raise ValueError("Synthetic data must not be written to ANSWERS")
    path.mkdir(parents=True, exist_ok=False)
    return path
