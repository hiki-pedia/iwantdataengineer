# ChartMaster Architecture

## v1 Direction

ChartMaster replaces the previous job-posting project with a market-data MLOps project. The dataset is larger, updates regularly, and gives clearer reasons to practice scheduled retraining and deployment.

## Data Flow

```text
market data provider
  -> Airflow collection task
  -> S3 raw data
  -> feature engineering task
  -> S3 processed features
  -> SageMaker training job
  -> evaluation task
  -> model artifact / endpoint
  -> FastAPI
  -> Electron dashboard
```

## Initial Assets

- Korea core: SK hynix, Samsung Electronics, POSCO DX, Hyundai Motor
- US core: Micron, SanDisk
- Experimental: SOXL, NASA, SPCX, RAM

## Why Core vs Experimental

Core assets should have enough history for baseline model training. Experimental assets are useful for collection and visualization, but may be weak model-training candidates because of short listing history or ETF structure.

## First Model

Target:

```text
future_5d_return > 0
```

This avoids pretending that exact price prediction is reliable and focuses the project on repeatable model training and evaluation.

