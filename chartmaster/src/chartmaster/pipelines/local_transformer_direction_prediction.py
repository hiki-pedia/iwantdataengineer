"""Train the selected Transformer-lite model and write latest 5-day direction predictions."""

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
    build_latest_sequence_dataset,
    build_sequence_dataset,
    find_best_lstm_threshold,
    fit_scaler,
    latest_sequence_prediction_frame,
    prepare_sequence_frame,
    train_transformer_direction,
)
from chartmaster.models.modeling_dataset import apply_window, split_by_fixed_dates
from chartmaster.pipelines.local_lstm_direction_training import load_feature_dataset
from chartmaster.pipelines.local_market_data_etl import select_assets
from chartmaster.storage.local import get_object_storage, relative_model_version_dir, serialize_pickle

if TYPE_CHECKING:
    from chartmaster.storage.postgres import PostgresMetadataStore


MODEL_NAME = "transformer_direction_5d_daily"
PREDICTION_COLUMN = "positive_probability_5d"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write daily Transformer-lite direction predictions.")
    parser.add_argument("--tier", choices=["core", "experimental", "all"], default="all")
    parser.add_argument("--market", choices=["KR", "US"], default=None)
    parser.add_argument("--symbols", nargs="*")
    parser.add_argument("--window", choices=["all_history", "post_2020", "recent_5y"], default="all_history")
    parser.add_argument("--as-of", default=None, help="Prediction as-of date, YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--sequence-length", type=int, default=60)
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


def local_report_paths() -> tuple[Path, Path]:
    report_dir = PROJECT_ROOT / "reports" / "predictions" / "direction_5d"
    return report_dir / "latest.json", report_dir / "latest.csv"


def write_local_reports(summary: dict[str, object], predictions: pd.DataFrame) -> None:
    json_path, csv_path = local_report_paths()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    predictions.to_csv(csv_path, index=False)


def build_prediction_rows(
    *,
    model,
    inference_dataset,
    threshold: float,
    assets_by_symbol: dict[str, object],
) -> pd.DataFrame:
    predictions = latest_sequence_prediction_frame(model, inference_dataset, PREDICTION_COLUMN)
    predictions["predicted_positive_5d"] = predictions[PREDICTION_COLUMN] >= threshold
    predictions["decision_threshold"] = threshold
    predictions["horizon_trading_days"] = 5
    predictions["model_name"] = MODEL_NAME
    predictions["market"] = predictions["symbol"].map(lambda symbol: assets_by_symbol[symbol].market)
    predictions["display_name"] = predictions["symbol"].map(lambda symbol: assets_by_symbol[symbol].display_name)
    return predictions[
        [
            "symbol",
            "display_name",
            "market",
            "as_of_date",
            "horizon_trading_days",
            PREDICTION_COLUMN,
            "decision_threshold",
            "predicted_positive_5d",
            "model_name",
        ]
    ].sort_values(["market", "symbol"]).reset_index(drop=True)


def merge_with_existing_predictions(storage, predictions: pd.DataFrame, market: str | None) -> pd.DataFrame:
    """Keep predictions from other markets when a market-specific DAG run finishes."""
    if market is None:
        return predictions
    path = PurePosixPath("reports") / "predictions" / "direction_5d" / "latest.csv"
    try:
        existing = storage.read_dataframe_csv(path)
    except Exception:
        return predictions
    if existing.empty or "market" not in existing.columns:
        return predictions
    remaining = existing[existing["market"] != market].copy()
    if remaining.empty:
        return predictions
    return pd.concat([remaining, predictions], ignore_index=True).sort_values(["market", "symbol"]).reset_index(drop=True)


def main() -> None:
    args = parse_args()
    as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date() if args.as_of else date.today()
    version = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    storage = get_object_storage(local_only=args.local_only)
    assets = select_assets(load_assets(), args.symbols, args.tier, args.market)
    if not assets:
        raise ValueError("No assets selected. Check --symbols, --tier, or --market.")
    assets_by_symbol = {asset.symbol: asset for asset in assets}

    metadata_store = None if args.skip_metadata else get_metadata_store()
    pipeline_run_id = metadata_store.start_pipeline_run("local_transformer_direction_prediction") if metadata_store else None

    try:
        raw_dataset = load_feature_dataset(storage, args.tier, args.market, args.symbols)
        labeled_frame = prepare_sequence_frame(raw_dataset)
        windowed_labeled = apply_window(labeled_frame, args.window, as_of)
        splits = split_by_fixed_dates(windowed_labeled)
        train_for_threshold = splits["train"]
        validation_for_threshold = splits["validation"]
        if train_for_threshold.empty or validation_for_threshold.empty:
            raise ValueError("Train and validation splits are required to select the daily prediction threshold.")

        threshold_scaler = fit_scaler(train_for_threshold)
        threshold_train_dataset = build_sequence_dataset(train_for_threshold, threshold_scaler, args.sequence_length)
        threshold_validation_dataset = build_sequence_dataset(
            validation_for_threshold,
            threshold_scaler,
            args.sequence_length,
        )
        threshold_model, threshold_training_summary = train_transformer_direction(
            threshold_train_dataset,
            threshold_validation_dataset,
            model_size=args.model_size,
            num_heads=args.num_heads,
            num_layers=args.num_layers,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
        )
        threshold, validation_metrics = find_best_lstm_threshold(threshold_model, threshold_validation_dataset)

        # After choosing the threshold, fit the daily model on every row whose 5-day label is already known.
        final_scaler = fit_scaler(windowed_labeled)
        final_train_dataset = build_sequence_dataset(windowed_labeled, final_scaler, args.sequence_length)
        final_model, final_training_summary = train_transformer_direction(
            final_train_dataset,
            build_sequence_dataset(validation_for_threshold, final_scaler, args.sequence_length),
            model_size=args.model_size,
            num_heads=args.num_heads,
            num_layers=args.num_layers,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
        )
        inference_frame = apply_window(raw_dataset, args.window, as_of)
        inference_dataset = build_latest_sequence_dataset(inference_frame, final_scaler, args.sequence_length)
        predictions = build_prediction_rows(
            model=final_model,
            inference_dataset=inference_dataset,
            threshold=threshold,
            assets_by_symbol=assets_by_symbol,
        )
        merged_predictions = merge_with_existing_predictions(storage, predictions, args.market)

        report_dir = PurePosixPath("reports") / "predictions" / "direction_5d"
        model_dir = relative_model_version_dir(MODEL_NAME, version)
        model_uri = storage.write_bytes(serialize_pickle(final_model.state_dict()), model_dir / "model_state.pkl")
        scaler_uri = storage.write_bytes(serialize_pickle(final_scaler), model_dir / "scaler.pkl")
        predictions_uri = storage.write_dataframe_csv(merged_predictions, report_dir / "latest.csv")
        history_predictions_uri = storage.write_dataframe_csv(predictions, report_dir / "history" / f"{version}.csv")

        summary = {
            "model_name": MODEL_NAME,
            "version": version,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "as_of": as_of.isoformat(),
            "window": args.window,
            "asset_count": len(assets),
            "market": args.market,
            "prediction_count": int(len(predictions)),
            "latest_prediction_count": int(len(merged_predictions)),
            "latest_markets": sorted(merged_predictions["market"].dropna().astype(str).unique().tolist()),
            "feature_columns": FEATURE_COLUMNS,
            "target_column": TARGET_COLUMN,
            "horizon_trading_days": 5,
            "sequence_length": args.sequence_length,
            "epochs": args.epochs,
            "decision_threshold": threshold,
            "threshold_selection_metric": "validation_f1",
            "validation_metrics": validation_metrics,
            "labeled_row_count": int(len(windowed_labeled)),
            "final_train_sequence_count": int(len(final_train_dataset.targets)),
            "threshold_train_sequence_count": int(len(threshold_train_dataset.targets)),
            "threshold_validation_sequence_count": int(len(threshold_validation_dataset.targets)),
            "model_uri": model_uri,
            "scaler_uri": scaler_uri,
            "predictions_uri": predictions_uri,
            "history_predictions_uri": history_predictions_uri,
            "threshold_training_summary": threshold_training_summary,
            "final_training_summary": final_training_summary,
        }
        latest_uri = storage.write_text(json.dumps(summary, indent=2), report_dir / "latest.json")
        history_uri = storage.write_text(json.dumps(summary, indent=2), report_dir / "history" / f"{version}.json")

        if not args.skip_local_report:
            write_local_reports(summary, merged_predictions)

        if metadata_store and pipeline_run_id:
            model_version_id = metadata_store.record_model_version(
                pipeline_run_id=pipeline_run_id,
                model_name=MODEL_NAME,
                version=version,
                tier=args.tier,
                artifact_uri=model_uri,
                train_row_count=len(final_train_dataset.targets),
                validation_row_count=len(threshold_validation_dataset.targets),
            )
            metadata_store.record_model_metrics(model_version_id, "validation", validation_metrics)
            metadata_store.record_dataset(
                pipeline_run_id=pipeline_run_id,
                dataset_type="daily_direction_predictions",
                storage_uri=predictions_uri,
                row_count=len(predictions),
            )
            metadata_store.finish_pipeline_run(pipeline_run_id, "success")
    except Exception as exc:
        if metadata_store and pipeline_run_id:
            metadata_store.finish_pipeline_run(pipeline_run_id, "failed", str(exc))
        raise

    print(f"Storage: {storage}")
    print(f"Metadata: {'postgres' if metadata_store else 'disabled'}")
    print(f"Model: {model_uri}")
    print(f"Scaler: {scaler_uri}")
    print(f"Predictions: {predictions_uri}")
    print(f"Report: {latest_uri}")
    print(f"History: {history_uri}")
    print(f"Prediction rows: {len(predictions)}")


if __name__ == "__main__":
    main()
