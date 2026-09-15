import pandas as pd

from chartmaster.models.deep_learning import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    build_latest_sequence_dataset,
    build_sequence_dataset,
    evaluate_lstm_direction,
    find_best_lstm_threshold,
    fit_scaler,
    prepare_sequence_frame,
    latest_sequence_prediction_frame,
    sequence_prediction_frame,
    train_lstm_direction,
    train_transformer_direction,
)


def make_sequence_data(row_count: int = 90) -> pd.DataFrame:
    rows = []
    for symbol in ["AAA", "BBB"]:
        for index in range(row_count):
            row = {
                "date": pd.Timestamp("2020-01-01") + pd.Timedelta(days=index),
                "symbol": symbol,
                TARGET_COLUMN: index % 4 in (0, 1),
            }
            for feature_index, column in enumerate(FEATURE_COLUMNS):
                row[column] = float((index + 1) / (feature_index + 1))
            rows.append(row)
    return pd.DataFrame(rows)


def test_sequence_dataset_uses_rolling_windows_per_symbol() -> None:
    frame = prepare_sequence_frame(make_sequence_data(20))
    scaler = fit_scaler(frame.iloc[:20])
    dataset = build_sequence_dataset(frame, scaler, window_size=5)

    assert dataset.features.shape == (32, 5, len(FEATURE_COLUMNS))
    assert dataset.targets.shape == (32,)
    assert dataset.symbols[:2] == ["AAA", "AAA"]


def test_latest_sequence_dataset_keeps_one_latest_window_per_symbol() -> None:
    frame = prepare_sequence_frame(make_sequence_data(20))
    scaler = fit_scaler(frame)
    dataset = build_latest_sequence_dataset(frame, scaler, window_size=5)

    assert dataset.features.shape == (2, 5, len(FEATURE_COLUMNS))
    assert dataset.symbols == ["AAA", "BBB"]
    assert dataset.dates == ["2020-01-20", "2020-01-20"]


def test_lstm_direction_model_trains_and_evaluates() -> None:
    frame = prepare_sequence_frame(make_sequence_data(80))
    train = frame.groupby("symbol", group_keys=False).head(55)
    validation = frame.groupby("symbol", group_keys=False).tail(25)
    scaler = fit_scaler(train)
    train_dataset = build_sequence_dataset(train, scaler, window_size=10)
    validation_dataset = build_sequence_dataset(validation, scaler, window_size=10)

    model, summary = train_lstm_direction(train_dataset, validation_dataset, epochs=1, hidden_size=8, batch_size=16)
    threshold, threshold_metrics = find_best_lstm_threshold(model, validation_dataset, step=0.2)
    metrics = evaluate_lstm_direction(model, validation_dataset, threshold=threshold)

    assert summary["epochs"] == 1
    assert 0.1 <= threshold <= 0.9
    assert metrics["f1"] == threshold_metrics["f1"]


def test_sequence_prediction_frame_keeps_symbol_date_keys() -> None:
    frame = prepare_sequence_frame(make_sequence_data(70))
    train = frame.groupby("symbol", group_keys=False).head(50)
    validation = frame.groupby("symbol", group_keys=False).tail(20)
    scaler = fit_scaler(train)
    train_dataset = build_sequence_dataset(train, scaler, window_size=10)
    validation_dataset = build_sequence_dataset(validation, scaler, window_size=10)

    model, _ = train_lstm_direction(train_dataset, validation_dataset, epochs=1, hidden_size=8, batch_size=16)
    predictions = sequence_prediction_frame(model, validation_dataset, "lstm_probability")

    assert list(predictions.columns) == ["symbol", "date", TARGET_COLUMN, "lstm_probability"]
    assert len(predictions) == len(validation_dataset.targets)
    assert predictions["symbol"].isin(["AAA", "BBB"]).all()


def test_latest_sequence_prediction_frame_uses_as_of_date() -> None:
    frame = prepare_sequence_frame(make_sequence_data(70))
    train = frame.groupby("symbol", group_keys=False).head(50)
    validation = frame.groupby("symbol", group_keys=False).tail(20)
    scaler = fit_scaler(train)
    train_dataset = build_sequence_dataset(train, scaler, window_size=10)
    validation_dataset = build_sequence_dataset(validation, scaler, window_size=10)
    inference_dataset = build_latest_sequence_dataset(frame, scaler, window_size=10)

    model, _ = train_lstm_direction(train_dataset, validation_dataset, epochs=1, hidden_size=8, batch_size=16)
    predictions = latest_sequence_prediction_frame(model, inference_dataset, "positive_probability_5d")

    assert list(predictions.columns) == ["symbol", "as_of_date", "positive_probability_5d"]
    assert len(predictions) == 2
    assert predictions["positive_probability_5d"].between(0, 1).all()


def test_transformer_direction_model_trains_and_evaluates() -> None:
    frame = prepare_sequence_frame(make_sequence_data(70))
    train = frame.groupby("symbol", group_keys=False).head(50)
    validation = frame.groupby("symbol", group_keys=False).tail(20)
    scaler = fit_scaler(train)
    train_dataset = build_sequence_dataset(train, scaler, window_size=10)
    validation_dataset = build_sequence_dataset(validation, scaler, window_size=10)

    model, summary = train_transformer_direction(
        train_dataset,
        validation_dataset,
        epochs=1,
        model_size=16,
        num_heads=4,
        num_layers=1,
        batch_size=16,
    )
    threshold, threshold_metrics = find_best_lstm_threshold(model, validation_dataset, step=0.2)
    metrics = evaluate_lstm_direction(model, validation_dataset, threshold=threshold)

    assert summary["epochs"] == 1
    assert 0.1 <= threshold <= 0.9
    assert metrics["f1"] == threshold_metrics["f1"]
