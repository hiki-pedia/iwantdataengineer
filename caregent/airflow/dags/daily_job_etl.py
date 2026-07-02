"""Caregent daily job ETL DAG.

Learning goals:
- Understand Airflow task boundaries.
- Practice idempotent PostgreSQL loading.
- Inspect task logs and retry behavior from the Airflow UI.
"""

from __future__ import annotations

import os
from datetime import timedelta

import pendulum
from airflow.decorators import dag, task

from caregent_etl.database import load_transformed_payload, payload_to_json
from caregent_etl.extract import extract_jobs
from caregent_etl.transform import transform_jobs


@dag(
    dag_id="daily_job_etl",
    description="Collect, normalize, load, and aggregate Caregent job postings.",
    schedule="0 15 * * *",
    start_date=pendulum.datetime(2026, 6, 1, tz="Asia/Seoul"),
    catchup=False,
    default_args={
        "owner": "caregent",
        "retries": 2,
        "retry_delay": timedelta(minutes=3),
    },
    tags=["caregent", "etl", "portfolio"],
)
def daily_job_etl():
    @task
    def extract() -> list[dict]:
        sample_path = os.getenv("CAREGENT_SAMPLE_JOBS_PATH")
        return extract_jobs(sample_path)

    @task
    def transform(raw_jobs: list[dict]) -> dict:
        return transform_jobs(raw_jobs)

    @task
    def load(payload: dict) -> dict:
        result = load_transformed_payload(payload)
        print(payload_to_json({"load_result": result, "trends": payload["trends"]}))
        return result

    load(transform(extract()))


daily_job_etl()
