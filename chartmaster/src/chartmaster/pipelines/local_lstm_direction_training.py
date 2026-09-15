"""Train pooled sequence direction models from stored chart features."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import pandas as pd
import torch

from chartmaster.config import get_postgres_dsn, load_assets
from chartmaster.models.deep_learning import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    build_sequence_dataset,
    evaluate_lstm_direction,
    find_best_lstm_threshold,
    fit_scaler,
    prepare_sequence_frame,
    train_lstm_direction,
    train_transformer_direction,
)
from chartmaster.models.direction import evaluate_fixed_direction_baseline, model_lift
from chartmaster.models.modeling_dataset import apply_window, split_by_fixed_dates
from chartmaster.pipelines.local_market_data_etl import select_assets
from chartmaster.storage.local import get_object_storage, relative_market_features_path, relative_model_version_dir, serialize_pickle

if TYPE_CHECKING:
    from chartmaster.storage.postgres import PostgresMetadataStore


MODEL_NAME_BY_ALGORITHM = {
    "lstm": "lstm_direction_5d",
    "transformer": "transformer_direction_5d",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a pooled sequence direction model.")
    parser.add_argument("--algorithm", choices=["lstm", "transformer"], default="lstm")
    parser.add_argument("--tier", choices=["core", "experimental", "all"], default="core")
    parser.add_argument("--market", choices=["KR", "US"], default=None)
    parser.add_argument("--symbols", nargs="*")
    parser.add_argument("--window", choices=["all_history", "post_2020", "recent_5y"], default="all_history")
    parser.add_argument("--as-of", default=None)
    parser.add_argument("--sequence-length", type=int, default=60)
    parser.add_argument("--hidden-size", type=int, default=32)
    parser.add_argument("--model-size", type=int, default=32)
    parser.add_argument("--num-heads", type=int, default=4)
    parser.add_argument("--num-layers", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--skip-metadata", action="store_true")
    return parser.parse_args()


def get_metadata_store() -> PostgresMetadataStore | None:
    """Return metadata store when PostgreSQL is configured."""
    if not get_postgres_dsn():
        return None
    from chartmaster.storage.postgres import PostgresMetadataStore

    store = PostgresMetadataStore.from_env()
    store.init_schema()
    return store


def load_feature_dataset(storage, tier: str, market: str | None, symbols: list[str] | None) -> pd.DataFrame:
    assets = select_assets(load_assets(), symbols, tier, market)
    frames = []
    for asset in assets:
        try:
            frame = storage.read_dataframe_csv(relative_market_features_path(asset.symbol))
        except Exception as exc:
            print(f"{asset.symbol}: skipped missing feature file ({exc})")
            continue
        frame["symbol"] = asset.symbol
        frame["display_name"] = asset.display_name
        frame["market"] = asset.market
        frames.append(frame)
    if not frames:
        raise ValueError("No feature files found.")
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    args = parse_args()
    as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date() if args.as_of else date.today()
    version = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    model_name = MODEL_NAME_BY_ALGORITHM[args.algorithm]

    storage = get_object_storage(local_only=args.local_only)
    metadata_store = None if args.skip_metadata else get_metadata_store()
    pipeline_run_id = metadata_store.start_pipeline_run("local_lstm_direction_training") if metadata_store else None

    try:
        dataset = load_feature_dataset(storage, args.tier, args.market, args.symbols)
        frame = prepare_sequence_frame(dataset)
        windowed = apply_window(frame, args.window, as_of)
        splits = split_by_fixed_dates(windowed)
        scaler = fit_scaler(splits["train"])
        train_dataset = build_sequence_dataset(splits["train"], scaler, args.sequence_length)
        validation_dataset = build_sequence_dataset(splits["validation"], scaler, args.sequence_length)
        test_dataset = build_sequence_dataset(splits["test"], scaler, args.sequence_length)

        if args.algorithm == "lstm":
            model, training_summary = train_lstm_direction(
                train_dataset,
                validation_dataset,
                hidden_size=args.hidden_size,
                epochs=args.epochs,
                batch_size=args.batch_size,
                learning_rate=args.learning_rate,
            )
        else:
            model, training_summary = train_transformer_direction(
                train_dataset,
                validation_dataset,
                model_size=args.model_size,
                num_heads=args.num_heads,
                num_layers=args.num_layers,
                epochs=args.epochs,
                batch_size=args.batch_size,
                learning_rate=args.learning_rate,
            )
        default_validation_metrics = evaluate_lstm_direction(model, validation_dataset)
        default_test_metrics = evaluate_lstm_direction(model, test_dataset)
        decision_threshold, validation_metrics = find_best_lstm_threshold(model, validation_dataset)
        test_metrics = evaluate_lstm_direction(model, test_dataset, threshold=decision_threshold)
        test_baselines = {
            "always_positive": evaluate_fixed_direction_baseline(
                pd.DataFrame({TARGET_COLUMN: pd.Series(test_dataset.targets.astype(bool))}),
                True,
            ),
            "always_negative": evaluate_fixed_direction_baseline(
                pd.DataFrame({TARGET_COLUMN: pd.Series(test_dataset.targets.astype(bool))}),
                False,
            ),
        }

        latest_probability = float(torch.sigmoid(model(torch.from_numpy(test_dataset.features[-1:]))).detach().numpy()[0])
        summary = {
            "model_name": model_name,
            "algorithm": args.algorithm,
            "version": version,
            "window": args.window,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "feature_columns": FEATURE_COLUMNS,
            "target_column": TARGET_COLUMN,
            "sequence_length": args.sequence_length,
            "hidden_size": args.hidden_size,
            "model_size": args.model_size,
            "num_heads": args.num_heads,
            "num_layers": args.num_layers,
            "epochs": args.epochs,
            "asset_count": int(windowed["symbol"].nunique()),
            "row_count": int(len(windowed)),
            "train_row_count": int(len(splits["train"])),
            "validation_row_count": int(len(splits["validation"])),
            "test_row_count": int(len(splits["test"])),
            "train_sequence_count": int(len(train_dataset.targets)),
            "validation_sequence_count": int(len(validation_dataset.targets)),
            "test_sequence_count": int(len(test_dataset.targets)),
            "decision_threshold": decision_threshold,
            "threshold_selection_metric": "validation_f1",
            "default_threshold_validation_metrics": default_validation_metrics,
            "default_threshold_test_metrics": default_test_metrics,
            "validation_metrics": validation_metrics,
            "test_metrics": test_metrics,
            "test_baselines": test_baselines,
            "test_lift_vs_always_positive": model_lift(test_metrics, test_baselines["always_positive"]),
            "latest_prediction": {
                "as_of": test_dataset.dates[-1],
                "symbol": test_dataset.symbols[-1],
                "horizon_trading_days": 5,
                "positive_probability": latest_probability,
                "predicted_positive": latest_probability >= decision_threshold,
                "threshold": decision_threshold,
            },
            "training_summary": training_summary,
        }

        artifact_dir = relative_model_version_dir(model_name, version)
        model_uri = storage.write_bytes(serialize_pickle(model.state_dict()), artifact_dir / "model_state.pkl")
        scaler_uri = storage.write_bytes(serialize_pickle(scaler), artifact_dir / "scaler.pkl")
        metrics_uri = storage.write_text(json.dumps(summary, indent=2), artifact_dir / "metrics.json")
        report_dir = PurePosixPath("reports") / "model_training" / model_name
        history_uri = storage.write_text(json.dumps(summary, indent=2), report_dir / "history" / f"{version}.json")
        latest_uri = storage.write_text(json.dumps(summary, indent=2), report_dir / "latest.json")

        if metadata_store and pipeline_run_id:
            model_version_id = metadata_store.record_model_version(
                pipeline_run_id=pipeline_run_id,
                model_name=model_name,
                version=version,
                tier=args.tier,
                artifact_uri=model_uri,
                train_row_count=len(train_dataset.targets),
                validation_row_count=len(validation_dataset.targets),
            )
            metadata_store.record_model_metrics(model_version_id, "validation", validation_metrics)
            metadata_store.record_model_metrics(model_version_id, "test", test_metrics)
            metadata_store.record_model_metrics(model_version_id, "test_baseline_always_positive", test_baselines["always_positive"])
            metadata_store.record_model_metrics(model_version_id, "test_lift_vs_always_positive", summary["test_lift_vs_always_positive"])
            metadata_store.record_dataset(
                pipeline_run_id=pipeline_run_id,
                dataset_type="sequence_model_training_report",
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
    print(f"Model: {model_uri}")
    print(f"Scaler: {scaler_uri}")
    print(f"Metrics: {metrics_uri}")
    print(f"Report: {latest_uri}")
    print(
        f"{args.algorithm.upper()} test_f1={test_metrics['f1']:.4f} "
        f"test_accuracy={test_metrics['accuracy']:.4f} "
        f"test_roc_auc={test_metrics.get('roc_auc', 0.0):.4f} "
        f"threshold={decision_threshold:.2f}"
    )


if __name__ == "__main__":
    main()
