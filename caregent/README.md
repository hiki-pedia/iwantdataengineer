# Caregent

Caregent is an AI Career Agent concept used as a data engineering learning portfolio. The goal is not to rush a finished app. The goal is to learn Airflow, ETL, PostgreSQL, and later AWS through a realistic project shape.

## v1 Goal

Build a local Airflow ETL pipeline that collects sample job postings, normalizes them, stores them in PostgreSQL, and creates skill trend data.

```text
sample_jobs.json
  -> Airflow daily_job_etl
  -> extract
  -> transform
  -> PostgreSQL load
  -> trend_data aggregation
```

## Project Layout

```text
caregent/
  airflow/dags/daily_job_etl.py
  data/sample_jobs.json
  docs/
  sql/001_init.sql
  src/caregent_etl/
  tests/
  docker-compose.yml
  requirements.txt
```

## Run Locally

From this directory:

```bash
docker compose up
```

Open Airflow:

- URL: `http://localhost:8080`
- Username: `airflow`
- Password: `airflow`

The DAG is named `daily_job_etl` and is scheduled for 15:00 every day.

## Query PostgreSQL

```bash
docker exec -it caregent-postgres psql -U caregent -d caregent
```

Useful checks:

```sql
SELECT company_name, position, category, industry FROM jobs ORDER BY company_name;
SELECT skill_name, frequency, trend_score FROM trend_data ORDER BY frequency DESC, skill_name;
```

## Local Tests

Install dependencies in a local Python environment, then run:

```bash
PYTHONPATH=src pytest
```

## Learning Notes

- [Learning roadmap](docs/learning-roadmap.md)
- [v1 architecture](docs/v1-architecture.md)

