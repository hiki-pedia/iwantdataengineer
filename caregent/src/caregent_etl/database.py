"""PostgreSQL loading helpers for the Caregent ETL pipeline."""

from __future__ import annotations

import json
import os
from typing import Any

import psycopg2
from psycopg2.extras import Json


DEFAULT_DSN = "dbname=caregent user=caregent password=caregent host=localhost port=5432"


def get_dsn() -> str:
    return os.getenv("CAREGENT_POSTGRES_DSN", DEFAULT_DSN)


def ensure_schema(dsn: str | None = None) -> None:
    with psycopg2.connect(dsn or get_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id SERIAL PRIMARY KEY,
                    source_id TEXT UNIQUE NOT NULL,
                    company_name TEXT NOT NULL,
                    position TEXT NOT NULL,
                    category TEXT NOT NULL,
                    industry TEXT NOT NULL,
                    location TEXT,
                    deadline DATE,
                    url TEXT,
                    description TEXT,
                    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                    collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );

                CREATE TABLE IF NOT EXISTS job_skills (
                    job_id INTEGER NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
                    skill_name TEXT NOT NULL,
                    PRIMARY KEY (job_id, skill_name)
                );

                CREATE TABLE IF NOT EXISTS trend_data (
                    skill_name TEXT PRIMARY KEY,
                    frequency INTEGER NOT NULL,
                    trend_score NUMERIC(8, 4) NOT NULL,
                    computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );

                CREATE TABLE IF NOT EXISTS users (
                    user_id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL
                );

                CREATE TABLE IF NOT EXISTS user_skills (
                    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    skill_name TEXT NOT NULL,
                    level TEXT NOT NULL DEFAULT 'beginner',
                    PRIMARY KEY (user_id, skill_name)
                );
                """
            )


def load_transformed_payload(payload: dict[str, Any], dsn: str | None = None) -> dict[str, int]:
    """Upsert jobs, replace job skills, and refresh trend rows."""
    ensure_schema(dsn)
    jobs = payload["jobs"]
    trends = payload["trends"]

    with psycopg2.connect(dsn or get_dsn()) as conn:
        with conn.cursor() as cur:
            for job in jobs:
                cur.execute(
                    """
                    INSERT INTO jobs (
                        source_id, company_name, position, category, industry,
                        location, deadline, url, description, raw_payload, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (source_id) DO UPDATE SET
                        company_name = EXCLUDED.company_name,
                        position = EXCLUDED.position,
                        category = EXCLUDED.category,
                        industry = EXCLUDED.industry,
                        location = EXCLUDED.location,
                        deadline = EXCLUDED.deadline,
                        url = EXCLUDED.url,
                        description = EXCLUDED.description,
                        raw_payload = EXCLUDED.raw_payload,
                        updated_at = now()
                    RETURNING job_id;
                    """,
                    (
                        job["source_id"],
                        job["company_name"],
                        job["position"],
                        job["category"],
                        job["industry"],
                        job["location"],
                        job["deadline"],
                        job["url"],
                        job["description"],
                        Json(job["raw_payload"]),
                    ),
                )
                job_id = cur.fetchone()[0]
                cur.execute("DELETE FROM job_skills WHERE job_id = %s;", (job_id,))
                cur.executemany(
                    "INSERT INTO job_skills (job_id, skill_name) VALUES (%s, %s);",
                    [(job_id, skill_name) for skill_name in job["skills"]],
                )

            cur.execute("TRUNCATE TABLE trend_data;")
            cur.executemany(
                """
                INSERT INTO trend_data (skill_name, frequency, trend_score)
                VALUES (%s, %s, %s);
                """,
                [
                    (trend["skill_name"], trend["frequency"], trend["trend_score"])
                    for trend in trends
                ],
            )

    return {"jobs_loaded": len(jobs), "trends_loaded": len(trends)}


def payload_to_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)

