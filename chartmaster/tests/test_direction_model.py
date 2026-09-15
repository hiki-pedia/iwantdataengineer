import pandas as pd

from chartmaster.models.direction import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    evaluate_direction_model,
    evaluate_fixed_direction_baseline,
    evaluate_train_positive_rate_baseline,
    find_best_score_threshold,
    find_best_threshold,
    model_lift,
    model_name_for_algorithm,
    predict_latest,
    prepare_model_frame,
    train_direction_model,
    train_random_forest_direction,
)


def make_model_data(row_count: int = 80) -> pd.DataFrame:
    rows = []
    for index in range(row_count):
        row = {
            "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=index),
            "symbol": "TEST",
            TARGET_COLUMN: index % 3 == 0,
        }
        for feature_index, column in enumerate(FEATURE_COLUMNS):
            row[column] = float((index + 1) * (feature_index + 1))
        rows.append(row)
    return pd.DataFrame(rows)


def test_prepare_model_frame_requires_model_columns() -> None:
    frame = prepare_model_frame(make_model_data())

    assert list(frame.columns) == ["date", "symbol", *FEATURE_COLUMNS, TARGET_COLUMN]
    assert frame[TARGET_COLUMN].dtype == bool


def test_random_forest_direction_model_trains_and_predicts_latest() -> None:
    frame = prepare_model_frame(make_model_data())
    train = frame.iloc[:60].copy()
    validation = frame.iloc[60:].copy()

    model = train_random_forest_direction(train, random_state=7)
    metrics = evaluate_direction_model(model, validation)
    prediction = predict_latest(model, frame)

    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert 0.0 <= prediction.positive_probability <= 1.0
    assert isinstance(prediction.predicted_positive, bool)


def test_direction_baselines_are_comparable_to_model_metrics() -> None:
    frame = prepare_model_frame(make_model_data())
    train = frame.iloc[:60].copy()
    validation = frame.iloc[60:].copy()
    model = train_random_forest_direction(train, random_state=7)

    model_metrics = evaluate_direction_model(model, validation)
    always_positive = evaluate_fixed_direction_baseline(validation, True)
    majority = evaluate_train_positive_rate_baseline(train, validation)
    lift = model_lift(model_metrics, always_positive)

    assert always_positive["predicted_positive_ratio"] == 1.0
    assert majority["train_positive_rate"] == train[TARGET_COLUMN].mean()
    assert "f1_lift" in lift


def test_best_threshold_is_selected_from_validation_f1() -> None:
    frame = prepare_model_frame(make_model_data())
    train = frame.iloc[:60].copy()
    validation = frame.iloc[60:].copy()
    model = train_random_forest_direction(train, random_state=7)

    threshold = find_best_threshold(model, validation, minimum_threshold=0.2, maximum_threshold=0.8, step=0.1)
    metrics = evaluate_direction_model(model, validation, threshold=threshold.threshold)
    prediction = predict_latest(model, frame, threshold=threshold.threshold)

    assert 0.2 <= threshold.threshold <= 0.8
    assert metrics["threshold"] == threshold.threshold
    assert prediction.threshold == threshold.threshold


def test_best_score_threshold_works_without_model_object() -> None:
    y_true = pd.Series([True, True, False, False])
    y_score = pd.Series([0.9, 0.7, 0.4, 0.2])

    threshold = find_best_score_threshold(y_true, y_score, minimum_threshold=0.3, maximum_threshold=0.8, step=0.1)

    assert 0.3 <= threshold.threshold <= 0.8
    assert threshold.metrics["f1"] == 1.0


def test_xgboost_direction_model_trains_on_small_dataset() -> None:
    frame = prepare_model_frame(make_model_data(120))
    train = frame.iloc[:90].copy()
    validation = frame.iloc[90:].copy()

    model = train_direction_model(train, "xgboost", random_state=7)
    metrics = evaluate_direction_model(model, validation)

    assert model_name_for_algorithm("xgboost") == "xgboost_direction_5d"
    assert 0.0 <= metrics["accuracy"] <= 1.0
