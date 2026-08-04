"""Local Phase 1 baseline model training."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pandas as pd

from chartmaster.config import get_postgres_dsn, load_assets
from chartmaster.models.baseline import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    evaluate_classifier,
    evaluate_naive_positive_baseline,
    train_baseline_classifier,
)
from chartmaster.storage.local import (
    ObjectStorage,
    get_object_storage,
    relative_market_features_path,
    relative_model_version_dir,
    serialize_pickle,
)

if TYPE_CHECKING:
    from chartmaster.storage.postgres import PostgresMetadataStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the local ChartMaster baseline model.")
    parser.add_argument(
        "--tier",
        choices=["core", "experimental", "all"],
        default="core",
        help="Asset tier to train on.",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Use local CHARTMASTER_DATA_DIR/chartmaster data instead of server2 SSH storage.",
    )
    parser.add_argument(
        "--skip-metadata",
        action="store_true",
        help="Do not write PostgreSQL metadata.",
    )
    parser.add_argument(
        "--validation-ratio",
        type=float,
        default=0.2,
        help="Time-ordered validation ratio.",
    )
    return parser.parse_args()


def get_metadata_store() -> PostgresMetadataStore | None:
    """Return metadata store when PostgreSQL is configured."""
    if not get_postgres_dsn():
        return None
    from chartmaster.storage.postgres import PostgresMetadataStore

    store = PostgresMetadataStore.from_env()
    store.init_schema()
    return store


def load_feature_dataset(storage: ObjectStorage, tier: str) -> pd.DataFrame:
    assets = load_assets()
    selected_assets = assets if tier == "all" else [asset for asset in assets if asset.modeling_tier == tier]

    frames: list[pd.DataFrame] = []
    for asset in selected_assets:
        path = relative_market_features_path(asset.symbol)
        try:
            frame = storage.read_dataframe_csv(path)
        except Exception:
            print(f"{asset.symbol}: skipped missing feature file {path}")
            continue
        frame["symbol"] = asset.symbol
        frames.append(frame)

    if not frames:
        raise ValueError("No feature files found. Run local_market_data_etl first.")

    dataset = pd.concat(frames, ignore_index=True)
    dataset = dataset.dropna(subset=FEATURE_COLUMNS + [TARGET_COLUMN]).copy()
    dataset["date"] = pd.to_datetime(dataset["date"])
    dataset = dataset.sort_values(["date", "symbol"]).reset_index(drop=True)
    return dataset


def split_time_ordered(dataset: pd.DataFrame, validation_ratio: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    split_index = int(len(dataset) * (1 - validation_ratio))
    if split_index <= 0 or split_index >= len(dataset):
        raise ValueError("Not enough rows to create train/validation split.")
    return dataset.iloc[:split_index].copy(), dataset.iloc[split_index:].copy()


def main() -> None:
    args = parse_args()
    storage = get_object_storage(local_only=args.local_only)
    metadata_store = None if args.skip_metadata else get_metadata_store()
    pipeline_run_id = metadata_store.start_pipeline_run("local_baseline_training") if metadata_store else None

    try:
        dataset = load_feature_dataset(storage, args.tier)
        train_data, validation_data = split_time_ordered(dataset, args.validation_ratio)

        model = train_baseline_classifier(train_data)
        model_metrics = evaluate_classifier(model, validation_data)
        naive_metrics = evaluate_naive_positive_baseline(validation_data)

        version = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        artifact_dir = relative_model_version_dir("baseline_classifier", version)
        model_path = artifact_dir / "model.pkl"
        metrics_path = artifact_dir / "metrics.json"
        train_path = artifact_dir / "train_dataset.csv"
        validation_path = artifact_dir / "validation_dataset.csv"

        metrics = {
            "model_name": "baseline_classifier",
            "version": version,
            "tier": args.tier,
            "row_count": int(len(dataset)),
            "train_row_count": int(len(train_data)),
            "validation_row_count": int(len(validation_data)),
            "feature_columns": FEATURE_COLUMNS,
            "target_column": TARGET_COLUMN,
            "model_metrics": model_metrics,
            "naive_positive_baseline_metrics": naive_metrics,
        }

        model_uri = storage.write_bytes(serialize_pickle(model), model_path)
        metrics_uri = storage.write_text(json.dumps(metrics, indent=2), metrics_path)
        train_uri = storage.write_dataframe_csv(train_data, train_path)
        validation_uri = storage.write_dataframe_csv(validation_data, validation_path)

        if metadata_store and pipeline_run_id:
            model_version_id = metadata_store.record_model_version(
                pipeline_run_id=pipeline_run_id,
                model_name="baseline_classifier",
                version=version,
                tier=args.tier,
                artifact_uri=model_uri,
                train_row_count=len(train_data),
                validation_row_count=len(validation_data),
            )
            metadata_store.record_model_metrics(model_version_id, "model", model_metrics)
            metadata_store.record_model_metrics(model_version_id, "naive_positive_baseline", naive_metrics)
            metadata_store.record_dataset(
                pipeline_run_id=pipeline_run_id,
                dataset_type="model_train_dataset",
                storage_uri=train_uri,
                row_count=len(train_data),
            )
            metadata_store.record_dataset(
                pipeline_run_id=pipeline_run_id,
                dataset_type="model_validation_dataset",
                storage_uri=validation_uri,
                row_count=len(validation_data),
            )
            metadata_store.finish_pipeline_run(pipeline_run_id, "success")
    except Exception as exc:
        if metadata_store and pipeline_run_id:
            metadata_store.finish_pipeline_run(pipeline_run_id, "failed", str(exc))
        raise

    print(f"Storage: {storage}")
    print(f"Metadata: {'postgres' if metadata_store else 'disabled'}")
    print(f"Trained baseline model: {model_uri}")
    print(f"Metrics: {metrics_uri}")
    print(f"Rows: total={len(dataset)} train={len(train_data)} validation={len(validation_data)}")
    print(f"Model f1={model_metrics.get('f1'):.4f}")
    print(f"Naive positive f1={naive_metrics.get('f1'):.4f}")


if __name__ == "__main__":
    main()
