# RandomForest 5거래일 방향 예측 평가

- model: `random_forest_direction_5d`
- version: `20260914T013854Z`
- window: `post_2020`
- trained: `25 / 29`
- skipped: `4`

## 상위 Test F1

| symbol | name | market | accuracy | precision | recall | f1 | roc_auc | latest_positive_prob |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| PG | Procter & Gamble | US | 0.5976 | 0.6168 | 0.7097 | 0.6600 | 0.6074 | 0.6758 |
| CAT | Caterpillar | US | 0.5325 | 0.5833 | 0.7071 | 0.6393 | 0.4840 | 0.5023 |
| 005490.KS | POSCO Holdings | KR | 0.5482 | 0.5714 | 0.6667 | 0.6154 | 0.5708 | 0.5153 |
| 022100.KS | POSCO DX | KR | 0.4639 | 0.4626 | 0.8718 | 0.6044 | 0.4937 | 0.6834 |
| 015760.KS | Korea Electric Power | KR | 0.4518 | 0.4333 | 0.6933 | 0.5333 | 0.5103 | 0.5860 |
| 000660.KS | SK hynix | KR | 0.4578 | 0.5753 | 0.4158 | 0.4828 | 0.4784 | 0.5959 |
| 030200.KS | KT | KR | 0.5361 | 0.6034 | 0.3933 | 0.4762 | 0.5678 | 0.3748 |
| MSFT | Microsoft | US | 0.4734 | 0.4348 | 0.3750 | 0.4027 | 0.4614 | 0.4681 |
| IBM | International Business Machines | US | 0.5089 | 0.4706 | 0.3000 | 0.3664 | 0.5310 | 0.5254 |
| 066570.KS | LG Electronics | KR | 0.4759 | 0.5227 | 0.2584 | 0.3459 | 0.5427 | 0.2807 |
| MU | Micron Technology | US | 0.3905 | 0.5714 | 0.1852 | 0.2797 | 0.4753 | 0.2198 |
| 000810.KS | Samsung Fire & Marine Insurance | KR | 0.4578 | 0.5385 | 0.1522 | 0.2373 | 0.5010 | 0.3918 |

## 스킵 종목

- `SNDK`: train rows 0 < 500
- `NASA`: train rows 0 < 500
- `SPCX`: train rows 0 < 500
- `RAM`: train rows 0 < 500
