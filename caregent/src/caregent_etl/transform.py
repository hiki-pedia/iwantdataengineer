"""Transform raw job postings into normalized Caregent records."""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from datetime import date
from typing import Any


SKILL_ALIASES = {
    "airflow": ["airflow", "apache airflow"],
    "aws": ["aws", "amazon web services"],
    "docker": ["docker", "container"],
    "fastapi": ["fastapi"],
    "git": ["git", "github"],
    "kafka": ["kafka", "apache kafka"],
    "kubernetes": ["kubernetes", "k8s"],
    "linux": ["linux", "ubuntu"],
    "mongodb": ["mongodb", "mongo"],
    "postgresql": ["postgresql", "postgres", "rds"],
    "python": ["python", "파이썬"],
    "redshift": ["redshift", "amazon redshift"],
    "spark": ["spark", "apache spark", "pyspark"],
    "sql": ["sql"],
}

CATEGORY_KEYWORDS = {
    "data_engineer": ["data engineer", "데이터 엔지니어", "etl", "pipeline", "파이프라인"],
    "backend": ["backend", "백엔드", "fastapi", "api"],
    "devops": ["devops", "sre", "kubernetes", "docker", "인프라"],
    "software": ["software", "개발자", "engineer"],
}

INDUSTRY_KEYWORDS = {
    "semiconductor": ["semiconductor", "반도체", "fab", "eda"],
    "it": ["it", "platform", "플랫폼", "software", "서비스"],
}


def transform_jobs(raw_jobs: list[dict[str, Any]]) -> dict[str, Any]:
    """Normalize, deduplicate, classify, and aggregate job postings."""
    seen_sources: set[str] = set()
    normalized_jobs: list[dict[str, Any]] = []

    for raw_job in raw_jobs:
        source_id = _source_id(raw_job)
        if source_id in seen_sources:
            continue
        seen_sources.add(source_id)

        text = _search_text(raw_job)
        skills = extract_skills(text)
        normalized_jobs.append(
            {
                "source_id": source_id,
                "company_name": _clean(raw_job.get("company_name")),
                "position": _clean(raw_job.get("position")),
                "category": classify(text, CATEGORY_KEYWORDS, default="unknown"),
                "industry": classify(text, INDUSTRY_KEYWORDS, default="unknown"),
                "location": _clean(raw_job.get("location")),
                "deadline": _parse_date(raw_job.get("deadline")),
                "url": _clean(raw_job.get("url")),
                "description": _clean(raw_job.get("description")),
                "skills": skills,
                "raw_payload": raw_job,
            }
        )

    trends = build_trends(normalized_jobs)
    return {"jobs": normalized_jobs, "trends": trends}


def extract_skills(text: str) -> list[str]:
    """Extract canonical skill names from free text."""
    lowered = text.lower()
    matched = []
    for skill_name, aliases in SKILL_ALIASES.items():
        if any(_contains_term(lowered, alias.lower()) for alias in aliases):
            matched.append(skill_name)
    return sorted(matched)


def classify(text: str, keyword_map: dict[str, list[str]], default: str) -> str:
    """Return the first class with a matching keyword."""
    lowered = text.lower()
    for label, keywords in keyword_map.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            return label
    return default


def build_trends(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate skill frequency and a simple normalized trend score."""
    counter = Counter(skill for job in jobs for skill in job["skills"])
    max_frequency = max(counter.values(), default=0)
    if max_frequency == 0:
        return []
    return [
        {
            "skill_name": skill_name,
            "frequency": frequency,
            "trend_score": round(frequency / max_frequency, 4),
        }
        for skill_name, frequency in sorted(counter.items())
    ]


def _source_id(raw_job: dict[str, Any]) -> str:
    stable_key = raw_job.get("url") or "|".join(
        [
            str(raw_job.get("company_name", "")),
            str(raw_job.get("position", "")),
            str(raw_job.get("deadline", "")),
        ]
    )
    return hashlib.sha256(stable_key.encode("utf-8")).hexdigest()


def _search_text(raw_job: dict[str, Any]) -> str:
    parts = [
        raw_job.get("company_name", ""),
        raw_job.get("position", ""),
        raw_job.get("category", ""),
        raw_job.get("industry", ""),
        raw_job.get("description", ""),
        " ".join(raw_job.get("skills", [])),
    ]
    return " ".join(str(part) for part in parts if part)


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _parse_date(value: Any) -> str | None:
    if not value:
        return None
    parsed = date.fromisoformat(str(value))
    return parsed.isoformat()


def _contains_term(text: str, term: str) -> bool:
    if re.search(r"[a-z0-9]", term):
        return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None
    return term in text

