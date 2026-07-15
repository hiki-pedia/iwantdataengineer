# ChartMaster Learning Roadmap

## Phase 1: Local Market Data Baseline

- Collect historical OHLCV data for the initial asset universe.
- Store raw CSV/Parquet locally.
- Build basic price, volume, turnover, volatility, and momentum features.
- Train a baseline classification model for 5-trading-day positive return.

## Phase 2: Airflow Local Automation

- Create `daily_market_data_etl`.
- Create `weekly_model_training`.
- Track task logs and retry behavior.
- Store local metadata in PostgreSQL.

## Phase 3: AWS S3 Data Lake

- Write raw market data to S3.
- Write processed features to S3.
- Preserve provider, symbol, and date partitions.

## Phase 4: SageMaker Training

- Trigger SageMaker training jobs from Airflow.
- Read processed features from S3.
- Write model artifacts and metrics back to S3.

## Phase 5: Evaluation and Deployment

- Compare model metrics with a naive baseline.
- Deploy only when validation criteria pass.
- Record accepted/rejected model versions.

## Phase 6: Electron Dashboard

- Show asset charts.
- Show prediction and model confidence.
- Show model version, metrics, and last training time.
- Show pipeline status from backend metadata.

## Study Log Template

- Date:
- Goal:
- Data source:
- Concepts:
- Commands:
- Result:
- Failure:
- Fix:
- Portfolio note:

