"""Baseline model contracts."""

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


FEATURE_COLUMNS = [
    "turnover_value",
    "return_1d",
    "return_5d",
    "return_20d",
    "volume_change_1d",
    "moving_average_5",
    "moving_average_20",
    "volatility_5",
    "volatility_20",
]

TARGET_COLUMN = "target_positive_5d_return"


def train_baseline_classifier(training_data: pd.DataFrame) -> object:
    """Train the first interpretable baseline classifier."""
    model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )
    model.fit(training_data[FEATURE_COLUMNS], training_data[TARGET_COLUMN].astype(bool))
    return model


def evaluate_classifier(model: object, validation_data: pd.DataFrame) -> dict[str, float]:
    """Evaluate a classifier with the project metrics."""
    y_true = validation_data[TARGET_COLUMN].astype(bool)
    y_pred = model.predict(validation_data[FEATURE_COLUMNS])
    y_score = model.predict_proba(validation_data[FEATURE_COLUMNS])[:, 1]

    metrics = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
    }
    if y_true.nunique() > 1:
        metrics["roc_auc"] = roc_auc_score(y_true, y_score)
    return {key: float(value) for key, value in metrics.items()}


def evaluate_naive_positive_baseline(validation_data: pd.DataFrame) -> dict[str, float]:
    """Evaluate a naive classifier that always predicts positive return."""
    y_true = validation_data[TARGET_COLUMN].astype(bool)
    y_pred = [True] * len(validation_data)
    metrics = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
    }
    return {key: float(value) for key, value in metrics.items()}
