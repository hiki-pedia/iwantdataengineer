# Phase 7 Ensemble Direction Model

- version: `20260915T022850Z`
- window: `all_history`
- asset_count: `29`
- aligned_test_rows: `2739`

## Ensemble Test Metrics

| Metric | Value |
| --- | ---: |
| Accuracy | 0.5655 |
| F1 | 0.7208 |
| ROC-AUC | 0.5044 |
| Threshold | 0.30 |
| Always-positive F1 | 0.7225 |
| F1 lift | -0.0017 |

## Component Metrics On Same Rows

| Model | Accuracy | F1 | ROC-AUC | Threshold |
| --- | ---: | ---: | ---: | ---: |
| xgboost | 0.5652 | 0.7201 | 0.5048 | 0.10 |
| lstm | 0.5630 | 0.7203 | 0.5077 | 0.34 |
| transformer | 0.5692 | 0.7237 | 0.5093 | 0.37 |

## Interpretation

이 결과는 투자 모델의 완성도가 아니라 Airflow/AWS로 자동 학습, 산출물 저장, 지표 비교를 운영하기 위한 기준 모델이다.
