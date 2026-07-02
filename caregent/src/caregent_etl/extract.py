"""Extract raw job postings from a reproducible local source.

The first milestone intentionally uses sample data instead of a live crawler so
Airflow, transformation, idempotent loading, and PostgreSQL can be studied
without website changes breaking the lesson.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_SAMPLE_PATH = Path(__file__).resolve().parents[2] / "data" / "sample_jobs.json"


def extract_jobs(sample_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Load raw job postings from JSON."""
    path = Path(sample_path) if sample_path else DEFAULT_SAMPLE_PATH
    with path.open("r", encoding="utf-8") as source:
        payload = json.load(source)

    if not isinstance(payload, list):
        raise ValueError(f"Expected a list of job postings in {path}")
    return payload

