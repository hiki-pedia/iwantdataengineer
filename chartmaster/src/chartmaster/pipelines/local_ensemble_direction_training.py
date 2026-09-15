"""Train an XGBoost/LSTM/Transformer ensemble for 5-day chart direction."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

import pandas as pd

from chartmaster.config import PROJECT_ROOT, get_postgres_dsn, load_assets
from chartmaster.models.deep_learning import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    build_sequence_dataset,
    find_best_lstm_threshold,
    fit_scaler,
    prepare_sequence_frame,
    sequence_prediction_frame,
    train_lstm_direction,
    train_transformer_direction,
)
from chartmaster.models.direction import (
    evaluate_fixed_direction_baseline,
    evaluate_scores,
    find_best_score_threshold,
    model_lift,
    predict_scores,
    prepare_model_frame,
    train_xgboost_direction,
)
from chartmaster.models.modeling_dataset import apply_window, split_by_fixed_dates
from chartmaster.pipelines.local_lstm_direction_training import load_feature_dataset
from chartmaster.pipelines.local_market_data_etl import select_assets
from chartmaster.storage.local import get_object_storage, relative_model_version_dir, serialize_pickle

if TYPE_CHECKING:
    from chartmaster.storage.postgres import PostgresMetadataStore


MODEL_NAME = "ensemble_direction_5d"
PROBABILITY_COLUMNS = ["xgboost_probability", "lstm_probability", "transformer_probability"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a pooled ChartMaster direction ensemble.")
    parser.add_argument("--tier", choices=["core", "experimental", "all"], default="core")
    parser.add_argument("--market", choices=["KR", "US"], default=None)
    parser.add_argument("--symbols", nargs="*")
    parser.add_argument("--window", choices=["all_history", "post_2020", "recent_5y"], default="all_history")
    parser.add_argument("--as-of", default=None, help="Dataset as-of date, YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--sequence-length", type=int, default=60)
    parser.add_argument("--hidden-size", type=int, default=32)
    parser.add_argument("--model-size", type=int, default=32)
    parser.add_argument("--num-heads", type=int, default=4)
    parser.add_argument("--num-layers", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--skip-metadata", action="store_true")
    parser.add_argument("--skip-local-report", action="store_true")
    return parser.parse_args()


def get_metadata_store() -> PostgresMetadataStore | None:
    """Return metadata store when PostgreSQL is configured."""
    if not get_postgres_dsn():
        return None
    from chartmaster.storage.postgres import PostgresMetadataStore

    store = PostgresMetadataStore.from_env()
    store.init_schema()
    return store


def xgboost_prediction_frame(
    models: dict[str, object],
    prediction_frame: pd.DataFrame,
    probability_column: str,
) -> pd.DataFrame:
    """Return keyed probabilities from trained per-symbol XGBoost models."""
    predictions = []

    for symbol, model in models.items():
        symbol_prediction = prediction_frame[prediction_frame["symbol"] == symbol].copy()
        if symbol_prediction.empty:
            continue
        scores = predict_scores(model, symbol_prediction)
        predictions.append(
            pd.DataFrame(
                {
                    "symbol": symbol_prediction["symbol"].astype(str),
                    "date": symbol_prediction["date"].dt.date.astype(str),
                    TARGET_COLUMN: symbol_prediction[TARGET_COLUMN].astype(bool),
                    probability_column: scores.to_numpy(),
                }
            )
        )

    if not predictions:
        raise ValueError("No XGBoost predictions were generated.")

    return pd.concat(predictions, ignore_index=True)


def train_xgboost_symbol_models(train_frame: pd.DataFrame) -> tuple[dict[str, object], dict[str, object]]:
    """Train one XGBoost model per symbol."""
    models = {}
    trained_symbols = []
    skipped_symbols = []

    for symbol, symbol_train in train_frame.groupby("symbol", sort=False):
        if symbol_train.empty:
            skipped_symbols.append({"symbol": str(symbol), "reason": "empty train split"})
            continue
        if symbol_train[TARGET_COLUMN].nunique() < 2:
            skipped_symbols.append({"symbol": str(symbol), "reason": "train split has one target class"})
            continue
        model = train_xgboost_direction(symbol_train)
        models[str(symbol)] = model
        trained_symbols.append(str(symbol))

    if not models:
        raise ValueError("No XGBoost symbol models were trainable.")

    return models, (
        {
            "trained_symbol_count": len(trained_symbols),
            "trained_symbols": trained_symbols,
            "skipped_symbol_count": len(skipped_symbols),
            "skipped_symbols": skipped_symbols,
        },
    )


def merge_prediction_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Inner-join model predictions so ensemble rows share the same symbol/date/target."""
    merged = frames[0]
    for frame in frames[1:]:
        merged = merged.merge(frame, on=["symbol", "date", TARGET_COLUMN], how="inner")
    merged["ensemble_probability"] = merged[PROBABILITY_COLUMNS].mean(axis=1)
    return merged.sort_values(["symbol", "date"]).reset_index(drop=True)


def evaluate_probability_column(
    validation_predictions: pd.DataFrame,
    test_predictions: pd.DataFrame,
    probability_column: str,
) -> dict[str, object]:
    threshold = find_best_score_threshold(
        validation_predictions[TARGET_COLUMN],
        validation_predictions[probability_column],
    )
    test_metrics = evaluate_scores(
        test_predictions[TARGET_COLUMN],
        test_predictions[probability_column],
        threshold=threshold.threshold,
    )
    return {
        "decision_threshold": threshold.threshold,
        "validation_metrics": threshold.metrics,
        "test_metrics": test_metrics,
    }


def local_report_paths() -> tuple[Path, Path, Path]:
    report_dir = PROJECT_ROOT / "reports" / "model_training" / MODEL_NAME
    return report_dir / "latest.json", report_dir / "latest_test_predictions.csv", report_dir / "latest_summary.md"


def write_local_reports(summary: dict[str, object], test_predictions: pd.DataFrame) -> None:
    json_path, csv_path, markdown_path = local_report_paths()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    test_predictions.to_csv(csv_path, index=False)

    metrics = summary["test_metrics"]
    baseline = summary["test_baselines"]["always_positive"]
    component_rows = []
    for name, row in summary["component_metrics"].items():
        test_metrics = row["test_metrics"]
        component_rows.append(
            f"| {name} | {test_metrics['accuracy']:.4f} | {test_metrics['f1']:.4f} | "
            f"{test_metrics.get('roc_auc', 0.0):.4f} | {row['decision_threshold']:.2f} |"
        )

    markdown = "\n".join(
        [
            "# Phase 7 Ensemble Direction Model",
            "",
            f"- version: `{summary['version']}`",
            f"- window: `{summary['window']}`",
            f"- asset_count: `{summary['asset_count']}`",
            f"- aligned_test_rows: `{summary['test_metrics']['row_count']:.0f}`",
            "",
            "## Ensemble Test Metrics",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| Accuracy | {metrics['accuracy']:.4f} |",
            f"| F1 | {metrics['f1']:.4f} |",
            f"| ROC-AUC | {metrics.get('roc_auc', 0.0):.4f} |",
            f"| Threshold | {summary['decision_threshold']:.2f} |",
            f"| Always-positive F1 | {baseline['f1']:.4f} |",
            f"| F1 lift | {summary['test_lift_vs_always_positive'].get('f1_lift', 0.0):.4f} |",
            "",
            "## Component Metrics On Same Rows",
            "",
            "| Model | Accuracy | F1 | ROC-AUC | Threshold |",
            "| --- | ---: | ---: | ---: | ---: |",
            *component_rows,
            "",
            "## Interpretation",
            "",
            "이 결과는 투자 모델의 완성도가 아니라 Airflow/AWS로 자동 학습, 산출물 저장, 지표 비교를 운영하기 위한 기준 모델이다.",
        ]
    )
    markdown_path.write_text(markdown + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date() if args.as_of else date.today()
    version = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    storage = get_object_storage(local_only=args.local_only)
    assets = select_assets(load_assets(), args.symbols, args.tier, args.market)
    if not assets:
        raise ValueError("No assets selected. Check --symbols, --tier, or --market.")

    metadata_store = None if args.skip_metadata else get_metadata_store()
    pipeline_run_id = metadata_store.start_pipeline_run("local_ensemble_direction_training") if metadata_store else None

    try:
        raw_dataset = load_feature_dataset(storage, args.tier, args.market, args.symbols)
        model_frame = prepare_model_frame(raw_dataset)
        sequence_frame = prepare_sequence_frame(raw_dataset)
        windowed_model_frame = apply_window(model_frame, args.window, as_of)
        windowed_sequence_frame = apply_window(sequence_frame, args.window, as_of)

        model_splits = split_by_fixed_dates(windowed_model_frame)
        sequence_splits = split_by_fixed_dates(windowed_sequence_frame)
        scaler = fit_scaler(sequence_splits["train"])
        train_dataset = build_sequence_dataset(sequence_splits["train"], scaler, args.sequence_length)
        validation_dataset = build_sequence_dataset(sequence_splits["validation"], scaler, args.sequence_length)
        test_dataset = build_sequence_dataset(sequence_splits["test"], scaler, args.sequence_length)

        print(f"Training XGBoost symbol models for {len(assets)} assets.")
        xgb_models, xgb_summary = train_xgboost_symbol_models(model_splits["train"])
        xgb_validation = xgboost_prediction_frame(
            xgb_models,
            model_splits["validation"],
            "xgboost_probability",
        )
        xgb_test = xgboost_prediction_frame(
            xgb_models,
            model_splits["test"],
            "xgboost_probability",
        )

        print(f"Training LSTM on {len(train_dataset.targets)} sequences.")
        lstm_model, lstm_training_summary = train_lstm_direction(
            train_dataset,
            validation_dataset,
            hidden_size=args.hidden_size,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
        )
        find_best_lstm_threshold(lstm_model, validation_dataset)
        lstm_validation = sequence_prediction_frame(lstm_model, validation_dataset, "lstm_probability")
        lstm_test = sequence_prediction_frame(lstm_model, test_dataset, "lstm_probability")

        print(f"Training Transformer-lite on {len(train_dataset.targets)} sequences.")
        transformer_model, transformer_training_summary = train_transformer_direction(
            train_dataset,
            validation_dataset,
            model_size=args.model_size,
            num_heads=args.num_heads,
            num_layers=args.num_layers,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
        )
        transformer_validation = sequence_prediction_frame(
            transformer_model,
            validation_dataset,
            "transformer_probability",
        )
        transformer_test = sequence_prediction_frame(transformer_model, test_dataset, "transformer_probability")

        validation_predictions = merge_prediction_frames([xgb_validation, lstm_validation, transformer_validation])
        test_predictions = merge_prediction_frames([xgb_test, lstm_test, transformer_test])
        threshold = find_best_score_threshold(
            validation_predictions[TARGET_COLUMN],
            validation_predictions["ensemble_probability"],
        )
        test_metrics = evaluate_scores(
            test_predictions[TARGET_COLUMN],
            test_predictions["ensemble_probability"],
            threshold=threshold.threshold,
        )
        test_baselines = {
            "always_positive": evaluate_fixed_direction_baseline(test_predictions, True),
            "always_negative": evaluate_fixed_direction_baseline(test_predictions, False),
        }
        component_metrics = {
            "xgboost": evaluate_probability_column(validation_predictions, test_predictions, "xgboost_probability"),
            "lstm": evaluate_probability_column(validation_predictions, test_predictions, "lstm_probability"),
            "transformer": evaluate_probability_column(validation_predictions, test_predictions, "transformer_probability"),
        }

        summary = {
            "model_name": MODEL_NAME,
            "version": version,
            "window": args.window,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "asset_count": len(assets),
            "assets": [asset.symbol for asset in assets],
            "feature_columns": FEATURE_COLUMNS,
            "target_column": TARGET_COLUMN,
            "horizon_trading_days": 5,
            "sequence_length": args.sequence_length,
            "epochs": args.epochs,
            "row_count": int(len(windowed_model_frame)),
            "train_row_count": int(len(model_splits["train"])),
            "validation_row_count": int(len(model_splits["validation"])),
            "test_row_count": int(len(model_splits["test"])),
            "train_sequence_count": int(len(train_dataset.targets)),
            "validation_sequence_count": int(len(validation_dataset.targets)),
            "test_sequence_count": int(len(test_dataset.targets)),
            "aligned_validation_row_count": int(len(validation_predictions)),
            "aligned_test_row_count": int(len(test_predictions)),
            "probability_columns": PROBABILITY_COLUMNS,
            "decision_threshold": threshold.threshold,
            "threshold_selection_metric": "validation_f1",
            "validation_metrics": threshold.metrics,
            "test_metrics": test_metrics,
            "test_baselines": test_baselines,
            "test_lift_vs_always_positive": model_lift(test_metrics, test_baselines["always_positive"]),
            "component_metrics": component_metrics,
            "xgboost_summary": xgb_summary,
            "lstm_training_summary": lstm_training_summary,
            "transformer_training_summary": transformer_training_summary,
        }

        artifact_dir = relative_model_version_dir(MODEL_NAME, version)
        xgb_uri = storage.write_bytes(serialize_pickle(xgb_models), artifact_dir / "xgboost_models.pkl")
        lstm_uri = storage.write_bytes(serialize_pickle(lstm_model.state_dict()), artifact_dir / "lstm_state.pkl")
        transformer_uri = storage.write_bytes(
            serialize_pickle(transformer_model.state_dict()),
            artifact_dir / "transformer_state.pkl",
        )
        scaler_uri = storage.write_bytes(serialize_pickle(scaler), artifact_dir / "scaler.pkl")
        metrics_uri = storage.write_text(json.dumps(summary, indent=2), artifact_dir / "metrics.json")

        report_dir = PurePosixPath("reports") / "model_training" / MODEL_NAME
        history_uri = storage.write_text(json.dumps(summary, indent=2), report_dir / "history" / f"{version}.json")
        latest_uri = storage.write_text(json.dumps(summary, indent=2), report_dir / "latest.json")
        predictions_uri = storage.write_dataframe_csv(test_predictions, report_dir / "latest_test_predictions.csv")

        if not args.skip_local_report:
            write_local_reports(summary, test_predictions)

        if metadata_store and pipeline_run_id:
            model_version_id = metadata_store.record_model_version(
                pipeline_run_id=pipeline_run_id,
                model_name=MODEL_NAME,
                version=version,
                tier=args.tier,
                artifact_uri=metrics_uri,
                train_row_count=len(train_dataset.targets),
                validation_row_count=len(validation_dataset.targets),
            )
            metadata_store.record_model_metrics(model_version_id, "validation", threshold.metrics)
            metadata_store.record_model_metrics(model_version_id, "test", test_metrics)
            metadata_store.record_model_metrics(
                model_version_id,
                "test_baseline_always_positive",
                test_baselines["always_positive"],
            )
            metadata_store.record_model_metrics(
                model_version_id,
                "test_lift_vs_always_positive",
                summary["test_lift_vs_always_positive"],
            )
            metadata_store.record_dataset(
                pipeline_run_id=pipeline_run_id,
                dataset_type="ensemble_model_training_report",
                storage_uri=latest_uri,
                row_count=1,
            )
            metadata_store.finish_pipeline_run(pipeline_run_id, "success")
    except Exception as exc:
        if metadata_store and pipeline_run_id:
            metadata_store.finish_pipeline_run(pipeline_run_id, "failed", str(exc))
        raise

    print(f"Storage: {storage}")
    print(f"Metadata: {'postgres' if metadata_store else 'disabled'}")
    print(f"XGBoost summary: {xgb_uri}")
    print(f"LSTM: {lstm_uri}")
    print(f"Transformer: {transformer_uri}")
    print(f"Scaler: {scaler_uri}")
    print(f"Metrics: {metrics_uri}")
    print(f"Report: {latest_uri}")
    print(f"Predictions: {predictions_uri}")
    print(
        f"ENSEMBLE test_f1={test_metrics['f1']:.4f} "
        f"test_accuracy={test_metrics['accuracy']:.4f} "
        f"test_roc_auc={test_metrics.get('roc_auc', 0.0):.4f} "
        f"threshold={threshold.threshold:.2f}"
    )


if __name__ == "__main__":
    main()
