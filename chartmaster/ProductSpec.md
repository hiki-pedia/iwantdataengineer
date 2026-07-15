# ChartMaster Product Specification

## 1. Project Purpose

ChartMaster is an Electron desktop application backed by an automated MLOps pipeline. It tracks a curated universe of Korean and US stocks/ETFs, trains prediction models on market data, and shows model outputs and training history to the user.

The product is intentionally learning-focused. The priority is to understand Airflow, AWS S3, SageMaker, model evaluation, and deployment automation.

## 2. Core Goals

1. Collect daily market data for selected Korean and US assets.
2. Store raw and processed data in a reproducible structure.
3. Generate price, volume, turnover, volatility, and momentum features.
4. Train models on a schedule or when enough new data accumulates.
5. Evaluate models before deployment.
6. Surface predictions, charts, and model metrics in an Electron desktop app.

## 3. Initial Asset Universe

### Korea Market

| Symbol | Name | Role |
| --- | --- | --- |
| `000660.KS` | SK hynix | Memory semiconductor core asset |
| `005930.KS` | Samsung Electronics | Korean semiconductor benchmark |
| `022100.KQ` | POSCO DX | Korean AI/industrial DX asset |
| `005380.KS` | Hyundai Motor | Korean non-semiconductor comparison asset |

### US Market

| Symbol | Name | Role |
| --- | --- | --- |
| `MU` | Micron | US memory semiconductor core asset |
| `SNDK` | SanDisk | US memory/storage asset |
| `SOXL` | Direxion Daily Semiconductor Bull 3X ETF | Leveraged semiconductor ETF |
| `NASA` | Tema Space Innovators ETF | Space economy ETF |
| `SPCX` | SpaceX | Space theme individual asset |
| `RAM` | Roundhill T-REX 2X Long DRAM Daily Target ETF | Experimental leveraged DRAM ETF |

## 4. Core vs Experimental Assets

Core assets are used for the first model training and evaluation loop.

- `000660.KS`
- `005930.KS`
- `022100.KQ`
- `005380.KS`
- `MU`
- `SNDK`

Experimental assets are collected and visualized first, but may be excluded from early model training if historical data is too short or the structure is too difficult to interpret.

- `SOXL`
- `NASA`
- `SPCX`
- `RAM`

## 5. Prediction Scope

The first model should not try to predict exact next-day closing price. The initial target is:

```text
Will the asset's 5-trading-day forward return be positive?
```

This keeps the first model interpretable and gives a clear classification metric.

## 6. Electron Application

The Electron app should show:

- Asset list grouped by Korea/US and core/experimental
- OHLCV chart
- Latest features
- Prediction result
- Model version and training date
- Evaluation metrics
- Airflow/SageMaker run history summary

## 7. Out of Scope for v1

- Real-money trading
- Automated order execution
- Portfolio allocation advice
- High-frequency or intraday prediction
- Investment recommendation claims

