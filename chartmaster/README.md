# ChartMaster

ChartMaster is a learning-first MLOps project for market data. It uses a small, curated stock and ETF universe to practice data collection, feature engineering, model retraining, evaluation, and deployment with Airflow and AWS.

The goal is not to build an investment recommendation system. The goal is to build a repeatable machine learning pipeline where new market data flows into storage, models are retrained on schedule, and results are visible in an Electron desktop application.

## Core Idea

```text
Market data
  -> Airflow
  -> S3 raw data
  -> feature engineering
  -> S3 processed data
  -> SageMaker training
  -> evaluation
  -> model registry/deployment
  -> Electron dashboard
```

## Initial Universe

Korea market:

- `000660.KS`: SK hynix
- `005930.KS`: Samsung Electronics
- `022100.KQ`: POSCO DX
- `005380.KS`: Hyundai Motor

US market:

- `MU`: Micron
- `SNDK`: SanDisk
- `SOXL`: Direxion Daily Semiconductor Bull 3X ETF
- `NASA`: Tema Space Innovators ETF
- `SPCX`: SpaceX
- `RAM`: Roundhill T-REX 2X Long DRAM Daily Target ETF

## Learning Phases

1. Local baseline: collect historical OHLCV data and train a simple model locally.
2. Airflow local automation: schedule collection, feature generation, training, and evaluation.
3. AWS S3: store raw and processed market data.
4. SageMaker training: trigger managed training jobs from Airflow.
5. Model evaluation and deployment: deploy only if metrics pass a threshold.
6. Electron dashboard: show charts, predictions, model metrics, and training history.

## Notes

- This project is for MLOps and data engineering practice, not financial advice.
- Newly listed assets such as `SPCX` and `RAM` may have limited history and should start as experimental assets.
- Leveraged ETFs such as `SOXL` and `RAM` are harder to model because daily reset and compounding behavior can distort longer-term returns.

