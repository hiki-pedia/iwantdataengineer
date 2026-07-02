# Caregent v1 Architecture

## Purpose

v1은 AI Career Agent 전체 제품을 완성하기보다, 데이터 엔지니어링 핵심 흐름을 작게 구현한다.

```text
sample job source
  -> Airflow daily_job_etl
    -> extract
    -> transform
      -> deduplicate
      -> extract skills
      -> classify category and industry
      -> build trend data
    -> load
      -> PostgreSQL jobs
      -> PostgreSQL job_skills
      -> PostgreSQL trend_data
```

## DAG

- DAG id: `daily_job_etl`
- Schedule: `0 15 * * *`
- Catchup: `false`
- Retry: 2 retries, 3 minute delay

## Tables

- `jobs`: normalized job posting rows with unique `source_id`
- `job_skills`: many-to-one skill rows per job
- `trend_data`: current skill frequency and normalized trend score
- `users`, `user_skills`: future Skill Gap Analysis practice tables

## Idempotency

`jobs.source_id` is generated from the source URL. The loader upserts `jobs`, replaces skills for each loaded job, and refreshes `trend_data`. Running the same DAG repeatedly should not create duplicate jobs.

