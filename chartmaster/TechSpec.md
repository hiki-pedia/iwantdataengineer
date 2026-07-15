# ChartMaster Technical Specification

## 1. Architecture

```text
Electron Desktop Application
  -> FastAPI Backend
    -> PostgreSQL metadata
    -> S3 processed data
    -> model prediction result

Airflow
  -> collect market data
  -> write S3 raw data
  -> build features
  -> write S3 processed data
  -> trigger SageMaker training
  -> evaluate model
  -> deploy model if accepted
```

## 2. Technology Stack

- Desktop: Electron
- Backend: FastAPI
- Workflow: Apache Airflow
- Storage: Amazon S3
- Metadata DB: PostgreSQL
- Training/Deployment: Amazon SageMaker
- Local baseline modeling: Python, pandas, scikit-learn

## 3. Data Sources

The initial provider can be `yfinance` or another public OHLCV provider for learning. Provider access should be abstracted so Korean market sources can later be improved with `pykrx` or another KRX-focused provider.

Required base fields:

- date
- open
- high
- low
- close
- adjusted_close
- volume

Derived fields:

- turnover_value = close * volume
- return_1d
- return_5d
- return_20d
- volume_change_1d
- moving_average_5
- moving_average_20
- volatility_5
- volatility_20

## 4. Asset Registry

The first asset registry lives in:

```text
config/assets.json
```

Each asset must define:

- symbol
- display_name
- market
- exchange
- asset_type
- group
- modeling_tier
- notes

## 5. Model Target

Initial target:

```text
target_positive_5d_return = future_5d_return > 0
```

Initial metrics:

- accuracy
- precision
- recall
- f1
- ROC-AUC if class balance allows

Deployment gate:

```text
Deploy only when validation f1 is above the configured threshold and the model beats a naive baseline.
```

## 6. Airflow DAGs

Planned DAGs:

- `daily_market_data_etl`
- `weekly_model_training`
- `model_evaluation_and_deploy`

The first implementation can combine these into one DAG locally, then split them when S3 and SageMaker are introduced.

## 7. AWS Flow

S3 layout:

```text
s3://chartmaster-{env}/raw/market_data/{provider}/{symbol}/date=YYYY-MM-DD/
s3://chartmaster-{env}/processed/features/{symbol}/as_of=YYYY-MM-DD/
s3://chartmaster-{env}/models/{model_name}/{version}/
s3://chartmaster-{env}/metrics/{model_name}/{version}/
```

SageMaker:

- Airflow submits training job.
- Training job reads processed features from S3.
- Model artifact is written to S3.
- Evaluation task checks metrics.
- Accepted model is registered/deployed.

## 8. Risk Notes

- `SPCX` and `RAM` are newly listed or recently available assets and may not provide enough historical training data.
- Leveraged ETFs such as `SOXL` and `RAM` should be treated carefully because daily reset mechanics make long-horizon behavior non-linear.
- ETF prices combine many underlying assets, so model interpretation should focus on pipeline practice rather than strong causal claims.
- Market prices are affected by news, sentiment, macro conditions, exchange rates, and liquidity. Sentiment and macro features can be added after the base OHLCV pipeline is stable.

