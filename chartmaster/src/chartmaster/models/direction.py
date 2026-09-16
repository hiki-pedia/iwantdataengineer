"""Direction prediction models for 5-trading-day chart movement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score


FEATURE_COLUMNS = [
    "return_1d",
    "return_5d",
    "return_20d",
    "return_60d",
    "volume_change_1d",
    "volume_ratio_20",
    "moving_average_5",
    "moving_average_20",
    "moving_average_60",
    "moving_average_120",
    "price_to_ma20",
    "price_to_ma60",
    "volatility_5",
    "volatility_20",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_histogram",
    "bollinger_percent_b_20",
    "bollinger_bandwidth_20",
    "atr_14",
    "momentum_10",
    "momentum_20",
    "breakout_high_20",
    "breakdown_low_20",
    "breakout_high_60",
    "breakdown_low_60",
]

TARGET_COLUMN = "target_positive_5d_return"
AlgorithmName = Literal["random_forest", "xgboost"]


@dataclass(frozen=True)
class PredictionResult:
    predicted_positive: bool
    positive_probability: float
    threshold: float = 0.5


@dataclass(frozen=True)
class ThresholdSearchResult:
    threshold: float
    metrics: dict[str, float]


def prepare_model_frame(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Return rows usable by the direction model."""
    required_columns = ["date", "symbol", *FEATURE_COLUMNS, TARGET_COLUMN]
    missing_columns = [column for column in required_columns if column not in dataframe.columns]
    if missing_columns:
        raise ValueError(f"Missing model columns: {', '.join(missing_columns)}")

    output = dataframe[required_columns].copy()
    output["date"] = pd.to_datetime(output["date"])
    output = output.dropna(subset=FEATURE_COLUMNS + [TARGET_COLUMN])
    output[TARGET_COLUMN] = output[TARGET_COLUMN].astype(bool)
    return output.sort_values("date").reset_index(drop=True)


def train_random_forest_direction(training_data: pd.DataFrame, random_state: int = 42) -> RandomForestClassifier:
    """Train an interpretable non-linear baseline for 5-day direction."""
    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=20,
        class_weight="balanced_subsample",
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(training_data[FEATURE_COLUMNS], training_data[TARGET_COLUMN])
    return model


def train_xgboost_direction(training_data: pd.DataFrame, random_state: int = 42) -> object:
    """Train a gradient boosting model commonly used for tabular chart features."""
    try:
        from xgboost import XGBClassifier
    except ImportError as exc:
        raise RuntimeError("xgboost is required. Install chartmaster requirements first.") from exc

    positive_count = int(training_data[TARGET_COLUMN].sum())
    negative_count = int(len(training_data) - positive_count)
    scale_pos_weight = negative_count / positive_count if positive_count else 1.0
    model = XGBClassifier(
        n_estimators=500,
        max_depth=3,
        learning_rate=0.03,
        subsample=0.85,
        colsample_bytree=0.85,
        min_child_weight=10,
        reg_lambda=2.0,
        objective="binary:logistic",
        eval_metric="logloss",
        tree_method="hist",
        scale_pos_weight=scale_pos_weight,
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(training_data[FEATURE_COLUMNS], training_data[TARGET_COLUMN].astype(int))
    return model


def train_direction_model(
    training_data: pd.DataFrame,
    algorithm: AlgorithmName,
    random_state: int = 42,
) -> object:
    """Train a direction model by algorithm name."""
    if algorithm == "random_forest":
        return train_random_forest_direction(training_data, random_state=random_state)
    if algorithm == "xgboost":
        return train_xgboost_direction(training_data, random_state=random_state)
    raise ValueError(f"Unsupported algorithm: {algorithm}")


def model_name_for_algorithm(algorithm: AlgorithmName) -> str:
    if algorithm == "random_forest":
        return "random_forest_direction_5d"
    if algorithm == "xgboost":
        return "xgboost_direction_5d"
    raise ValueError(f"Unsupported algorithm: {algorithm}")


def evaluate_scores(y_true: pd.Series, y_score: pd.Series, threshold: float = 0.5) -> dict[str, float]:
    """Evaluate binary scores with a configurable decision threshold."""
    y_pred = y_score >= threshold
    metrics = {
        "row_count": float(len(y_true)),
        "positive_ratio": float(y_true.mean()),
        "predicted_positive_ratio": float(y_pred.mean()),
        "threshold": float(threshold),
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
    }
    if y_true.nunique() > 1:
        metrics["roc_auc"] = roc_auc_score(y_true, y_score)
    return {key: float(value) for key, value in metrics.items()}


def find_best_score_threshold(
    y_true: pd.Series,
    y_score: pd.Series,
    minimum_threshold: float = 0.1,
    maximum_threshold: float = 0.9,
    step: float = 0.01,
) -> ThresholdSearchResult:
    """Find the score threshold with the best validation F1 score."""
    if step <= 0:
        raise ValueError("step must be positive")
    candidates = []
    threshold = minimum_threshold
    while threshold <= maximum_threshold + 1e-9:
        metrics = evaluate_scores(y_true, y_score, threshold=round(threshold, 4))
        candidates.append((metrics["f1"], metrics["precision"], -abs(metrics["threshold"] - 0.5), metrics))
        threshold += step
    best_metrics = max(candidates, key=lambda item: item[:3])[3]
    return ThresholdSearchResult(threshold=best_metrics["threshold"], metrics=best_metrics)


def predict_scores(model: object, data: pd.DataFrame) -> pd.Series:
    """Return positive-class probabilities for model rows."""
    return pd.Series(model.predict_proba(data[FEATURE_COLUMNS])[:, 1], index=data.index)


def evaluate_direction_model(model: object, data: pd.DataFrame, threshold: float = 0.5) -> dict[str, float]:
    """Evaluate a binary direction model."""
    y_true = data[TARGET_COLUMN]
    y_score = predict_scores(model, data)
    return evaluate_scores(y_true, y_score, threshold=threshold)


def find_best_threshold(
    model: object,
    validation_data: pd.DataFrame,
    minimum_threshold: float = 0.1,
    maximum_threshold: float = 0.9,
    step: float = 0.01,
) -> ThresholdSearchResult:
    """Find the validation threshold with the best F1 score."""
    y_true = validation_data[TARGET_COLUMN]
    y_score = predict_scores(model, validation_data)
    return find_best_score_threshold(
        y_true,
        y_score,
        minimum_threshold=minimum_threshold,
        maximum_threshold=maximum_threshold,
        step=step,
    )


def evaluate_fixed_direction_baseline(data: pd.DataFrame, predicted_positive: bool) -> dict[str, float]:
    """Evaluate a classifier that always predicts one direction."""
    y_true = data[TARGET_COLUMN]
    y_pred = pd.Series([predicted_positive] * len(data), index=data.index)
    metrics = {
        "row_count": float(len(data)),
        "positive_ratio": float(y_true.mean()),
        "predicted_positive_ratio": float(y_pred.mean()),
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
    }
    return {key: float(value) for key, value in metrics.items()}


def evaluate_train_positive_rate_baseline(training_data: pd.DataFrame, data: pd.DataFrame) -> dict[str, float]:
    """Evaluate a baseline that predicts the majority direction from the training split."""
    train_positive_rate = float(training_data[TARGET_COLUMN].mean())
    predicted_positive = train_positive_rate >= 0.5
    metrics = evaluate_fixed_direction_baseline(data, predicted_positive)
    metrics["train_positive_rate"] = train_positive_rate
    return metrics


def model_lift(model_metrics: dict[str, float], baseline_metrics: dict[str, float]) -> dict[str, float]:
    """Return simple metric deltas against a baseline."""
    comparable_metrics = ("accuracy", "precision", "recall", "f1", "roc_auc")
    return {
        f"{metric}_lift": float(model_metrics[metric] - baseline_metrics[metric])
        for metric in comparable_metrics
        if metric in model_metrics and metric in baseline_metrics
    }


def feature_importance(model: object) -> list[dict[str, float | str]]:
    """Return sorted feature importances."""
    importances = getattr(model, "feature_importances_", None)
    if importances is None:
        return []
    rows = [
        {"feature": feature, "importance": float(importance)}
        for feature, importance in zip(FEATURE_COLUMNS, importances, strict=True)
    ]
    return sorted(rows, key=lambda row: float(row["importance"]), reverse=True)


def predict_latest(model: object, dataframe: pd.DataFrame, threshold: float = 0.5) -> PredictionResult:
    """Predict the latest available feature row."""
    latest = dataframe.sort_values("date").iloc[-1:]
    probability = float(model.predict_proba(latest[FEATURE_COLUMNS])[:, 1][0])
    return PredictionResult(predicted_positive=probability >= threshold, positive_probability=probability, threshold=threshold)
