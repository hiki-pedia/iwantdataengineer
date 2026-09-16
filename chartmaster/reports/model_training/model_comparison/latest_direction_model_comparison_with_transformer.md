# Direction Model Comparison with Transformer-lite

| algorithm | scope | window | train_rows | train_sequences | threshold | accuracy | f1 | default_f1 | always_positive_f1 | f1_lift | roc_auc |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| random_forest | per_symbol | all_history | 210928 |  | per_symbol | 0.5494 | 0.6715 | 0.2252 | 0.7122 | -0.0407 | 0.5252 |
| xgboost | per_symbol | all_history | 210928 |  | per_symbol | 0.5555 | 0.6817 | 0.2779 | 0.7122 | -0.0305 | 0.5417 |
| lstm | pooled | all_history | 210928 | 209453 | 0.34 | 0.5673 | 0.7238 | 0.4040 | 0.7259 | -0.0021 | 0.5091 |
| transformer | pooled | all_history | 210928 | 209453 | 0.37 | 0.5733 | 0.7271 | 0.4832 | 0.7259 | +0.0011 | 0.5133 |
