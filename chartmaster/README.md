# ChartMaster

ChartMaster is a learning-first MLOps and AI project for market data. It starts with a local server1/server2 data platform, expands the stock and ETF universe, then moves the proven structure to AWS.

The goal is not to build an investment recommendation system. The goal is to build a repeatable machine learning pipeline where new market data flows into storage, models are retrained on schedule, and results are visible in an Electron desktop application.

## Core Idea

```text
Market data
  -> Airflow
  -> server2 raw data
  -> feature engineering
  -> server2 processed data
  -> external news/document collection
  -> RAG and sentiment signals
  -> local/SageMaker training
  -> evaluation
  -> model registry/deployment
  -> Electron dashboard
```

## Initial Universe

Korea market:

- `000660.KS`: SK hynix
- `005930.KS`: Samsung Electronics
- `022100.KS`: POSCO DX
- `005380.KS`: Hyundai Motor
- `005490.KS`: POSCO Holdings
- `000810.KS`: Samsung Fire & Marine Insurance
- `066570.KS`: LG Electronics
- `034730.KS`: SK Inc.
- `030200.KS`: KT
- `015760.KS`: Korea Electric Power
- `055550.KS`: Shinhan Financial Group
- `105560.KS`: KB Financial Group

US market:

- `MU`: Micron
- `WDC`: Western Digital
- `SPY`: SPDR S&P 500 ETF Trust
- `QQQ`: Invesco QQQ Trust
- `AAPL`: Apple
- `MSFT`: Microsoft
- `IBM`: International Business Machines
- `KO`: Coca-Cola
- `JPM`: JPMorgan Chase
- `XOM`: Exxon Mobil
- `CAT`: Caterpillar
- `PG`: Procter & Gamble
- `SNDK`: SanDisk
- `SOXL`: Direxion Daily Semiconductor Bull 3X ETF
- `NASA`: Tema Space Innovators ETF
- `SPCX`: SpaceX
- `RAM`: Roundhill T-REX 2X Long DRAM Daily Target ETF

## Learning Phases

1. Local baseline and server2 storage: backfill OHLCV data, store raw/processed files, and record PostgreSQL metadata.
2. Airflow local automation: schedule Korean and US market collection with catchup, overlap merge, retry, and deduplication.
3. Electron dashboard mock prototype: build the desktop information structure before modeling and RAG are stable.
4. FastAPI service boundary: define API contracts and keep Electron away from direct file/DB access.
5. Data quality and reprocessing: validate coverage, duplicates, backfills, and idempotent reruns.
6. Operational reliability: document backups, restore drills, Airflow recovery, logs, and health checks.
7. Machine learning pipeline: train baseline models and record artifacts/metrics with reproducible metadata.
8. RAG external factor layer: collect news/reports/events and connect external explanations to events/reports.
9. AWS S3/RDS migration: move the proven local storage/metadata pattern to managed AWS services.
10. SageMaker and observability: run managed training and inspect CloudWatch logs, retry behavior, backup policy, and cost.

## Notes

- This project is for MLOps and data engineering practice, not financial advice.
- Newly listed assets such as `SPCX` and `RAM` may have limited history and should start as experimental assets.
- Leveraged ETFs such as `SOXL` and `RAM` are harder to model because daily reset and compounding behavior can distort longer-term returns.
- AI reports are explanatory study outputs, not investment recommendations.

## Phase 1 Server2 Run

Create the local Python environment:

```bash
cd chartmaster
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Collect OHLCV data and build basic features:

```bash
PYTHONPATH=src .venv/bin/python -m chartmaster.pipelines.local_market_data_etl \
  --tier all \
  --start 2024-01-01 \
  --end 2026-07-01
```

Train the first baseline classifier:

```bash
PYTHONPATH=src .venv/bin/python -m chartmaster.pipelines.local_baseline_training \
  --tier core
```

By default, the scripts read `.env` and use server2 when `CHARTMASTER_SERVER2_*` and `CHARTMASTER_POSTGRES_DSN` are configured.

Current server2 targets:

```text
File storage: /home/dnhs02/iwantdataengineer/chartmaster
Metadata DB: PostgreSQL chartmaster database on port 5432
```

Use local-only mode only for isolated debugging:

```bash
PYTHONPATH=src .venv/bin/python -m chartmaster.pipelines.local_market_data_etl \
  --local-only \
  --skip-metadata \
  --symbols MU \
  --start 2024-01-01 \
  --end 2024-01-10
```

Local fallback outputs are written under `chartmaster/data/`, which is intentionally ignored by Git.

## Phase 2 Airflow Run

ChartMaster Airflow runs on server1 and writes data to server2 through the existing `.env` settings.

```bash
cd /home/dnhs01/iwantdataengineer/chartmaster
docker compose --env-file ../.env up -d --build
```

Airflow UI:

```text
http://localhost:8081
```

Default local login is controlled by `.env`:

```text
AIRFLOW_ADMIN_USER=chartmaster
AIRFLOW_ADMIN_PASSWORD=change-this-password
```

Scheduled DAGs:

- `daily_kr_market_data_etl`: Korean market daily OHLCV, 16:10 Asia/Seoul on weekdays.
- `daily_us_market_data_etl`: US market daily OHLCV, 17:30 America/New_York on weekdays.

Both DAGs use Airflow catchup. If server1 is off at the scheduled time, Airflow creates the missed run when the scheduler comes back. Each run fetches a 10-day overlap window and merges by date, so existing backfilled history is not replaced by a short daily file.

## Phase 5 Data Quality

Run a read-only quality check without saving a report:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python \
  -m chartmaster.pipelines.local_market_data_quality \
  --tier all \
  --no-write-report
```

Rebuild processed features from stored raw data. The command is a dry run unless `--write` is explicitly provided:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python \
  -m chartmaster.pipelines.local_market_data_reprocess \
  --market KR \
  --tier all
```

The scheduled KR and US DAGs run their market quality check after collection. Error-level findings fail the quality task, while provider anomalies and long market gaps remain visible as warnings in server2 JSON reports.

Korean market runs add a curation step between collection and validation. It preserves Yahoo raw files, stores pykrx's Naver-backed comparison rows separately, repairs confirmed OHLC anomalies and missing sessions in the curated layer, and regenerates features from that canonical result.

Latest Phase 5 verification:

- 29 assets passed the quality check.
- Error count: 0.
- Warning count: 1.
- Korean manual validation run: collect, curate, and validate tasks succeeded.
- Recent KR and US scheduled Airflow runs succeeded.
- KRX-authenticated raw-source verification is tracked as a later enhancement, not a Phase 5 blocker.

Phase 5 references:

- `docs/asset-universe.md`
- `docs/data-source-coverage.md`
- `docs/data-quality-strategy.md`
- `docs/backfill-reprocessing-runbook.md`

## Phase 6 Operational Reliability

Phase 6 defines normal operating state, backup targets, restore checks, and failure-drill order before moving the platform to AWS.

Current Phase 6 verification:

- Server 1 Airflow/FastAPI containers are running, with webserver/API health checks healthy.
- Server 2 SSH and `chartmaster-postgres` are reachable.
- Server 2 file storage backup was created and tar listing was verified.
- ChartMaster PostgreSQL metadata dump was created with the Server 2 PostgreSQL container's `pg_dump`.
- The metadata dump was restored into a temporary database with `ON_ERROR_STOP=1`, then the temporary database was dropped.
- FastAPI container restart drill passed, and `/health` plus Docker health recovered.

Phase 6 references:

- `docs/operation-runbook.md`
- `docs/backup-restore-runbook.md`
- `docs/failure-drill-report.md`
- `docs/blog/06-phase6-operational-reliability.md`
