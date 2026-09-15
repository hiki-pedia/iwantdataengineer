"""Train per-symbol 5-day direction models from stored chart features."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import pandas as pd

from chartmaster.config import Asset, get_postgres_dsn, load_assets
from chartmaster.models.direction import (
    AlgorithmName,
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    evaluate_direction_model,
    evaluate_fixed_direction_baseline,
    evaluate_train_positive_rate_baseline,
    feature_importance,
    find_best_threshold,
    model_lift,
    model_name_for_algorithm,
    predict_latest,
    prepare_model_frame,
    train_direction_model,
)
from chartmaster.models.modeling_dataset import apply_window, split_by_fixed_dates
from chartmaster.pipelines.local_market_data_etl import select_assets
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
    parser = argparse.ArgumentParser(description="Train per-symbol ChartMaster direction models.")
    parser.add_argument("--algorithm", choices=["random_forest", "xgboost"], default="random_forest")
    parser.add_argument("--tier", choices=["core", "experimental", "all"], default="core")
    parser.add_argument("--market", choices=["KR", "US"], default=None)
    parser.add_argument("--symbols", nargs="*")
    parser.add_argument("--window", choices=["all_history", "post_2020", "recent_5y"], default="post_2020")
    parser.add_argument("--as-of", default=None, help="Dataset as-of date, YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--min-train-rows", type=int, default=500)
    parser.add_argument("--min-validation-rows", type=int, default=100)
    parser.add_argument("--min-test-rows", type=int, default=20)
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


def safe_symbol(symbol: str) -> str:
    return symbol.replace("/", "_").replace(".", "_")


def load_symbol_features(storage: ObjectStorage, asset: Asset) -> pd.DataFrame:
    path = relative_market_features_path(asset.symbol)
    frame = storage.read_dataframe_csv(path)
    frame["symbol"] = asset.symbol
    return frame


def split_is_trainable(
    splits: dict[str, pd.DataFrame],
    *,
    min_train_rows: int,
    min_validation_rows: int,
    min_test_rows: int,
) -> tuple[bool, str | None]:
    if len(splits["train"]) < min_train_rows:
        return False, f"train rows {len(splits['train'])} < {min_train_rows}"
    if len(splits["validation"]) < min_validation_rows:
        return False, f"validation rows {len(splits['validation'])} < {min_validation_rows}"
    if len(splits["test"]) < min_test_rows:
        return False, f"test rows {len(splits['test'])} < {min_test_rows}"
    for name, split in splits.items():
        if split[TARGET_COLUMN].nunique() < 2:
            return False, f"{name} split has one target class"
    return True, None


def train_asset_model(
    *,
    storage: ObjectStorage,
    asset: Asset,
    version: str,
    model_name: str,
    algorithm: AlgorithmName,
    window: str,
    as_of: date,
    min_train_rows: int,
    min_validation_rows: int,
    min_test_rows: int,
) -> dict[str, object]:
    features = load_symbol_features(storage, asset)
    model_frame = prepare_model_frame(features)
    windowed = apply_window(model_frame, window, as_of)
    splits = split_by_fixed_dates(windowed)
    trainable, reason = split_is_trainable(
        splits,
        min_train_rows=min_train_rows,
        min_validation_rows=min_validation_rows,
        min_test_rows=min_test_rows,
    )

    base_result = {
        "symbol": asset.symbol,
        "display_name": asset.display_name,
        "market": asset.market,
        "tier": asset.modeling_tier,
        "window": window,
        "row_count": int(len(windowed)),
        "train_row_count": int(len(splits["train"])),
        "validation_row_count": int(len(splits["validation"])),
        "test_row_count": int(len(splits["test"])),
    }
    if not trainable:
        return {**base_result, "status": "skipped", "reason": reason}

    model = train_direction_model(splits["train"], algorithm)
    default_threshold_validation_metrics = evaluate_direction_model(model, splits["validation"])
    default_threshold_test_metrics = evaluate_direction_model(model, splits["test"])
    threshold_search = find_best_threshold(model, splits["validation"])
    validation_metrics = threshold_search.metrics
    test_metrics = evaluate_direction_model(model, splits["test"], threshold=threshold_search.threshold)
    validation_baselines = {
        "always_positive": evaluate_fixed_direction_baseline(splits["validation"], True),
        "always_negative": evaluate_fixed_direction_baseline(splits["validation"], False),
        "train_positive_rate": evaluate_train_positive_rate_baseline(splits["train"], splits["validation"]),
    }
    test_baselines = {
        "always_positive": evaluate_fixed_direction_baseline(splits["test"], True),
        "always_negative": evaluate_fixed_direction_baseline(splits["test"], False),
        "train_positive_rate": evaluate_train_positive_rate_baseline(splits["train"], splits["test"]),
    }
    latest_prediction = predict_latest(model, windowed, threshold=threshold_search.threshold)

    symbol_dir = relative_model_version_dir(model_name, version) / f"symbol={safe_symbol(asset.symbol)}"
    model_path = symbol_dir / "model.pkl"
    metrics_path = symbol_dir / "metrics.json"
    importance_path = symbol_dir / "feature_importance.csv"

    importances = feature_importance(model)
    metrics = {
        **base_result,
        "status": "trained",
        "model_name": model_name,
        "algorithm": algorithm,
        "version": version,
        "target_column": TARGET_COLUMN,
        "feature_columns": FEATURE_COLUMNS,
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "decision_threshold": threshold_search.threshold,
        "threshold_selection_metric": "validation_f1",
        "default_threshold_validation_metrics": default_threshold_validation_metrics,
        "default_threshold_test_metrics": default_threshold_test_metrics,
        "validation_baselines": validation_baselines,
        "test_baselines": test_baselines,
        "test_lift_vs_always_positive": model_lift(test_metrics, test_baselines["always_positive"]),
        "test_lift_vs_train_positive_rate": model_lift(test_metrics, test_baselines["train_positive_rate"]),
        "latest_prediction": {
            "as_of": str(pd.to_datetime(windowed["date"]).max().date()),
            "horizon_trading_days": 5,
            "predicted_positive": latest_prediction.predicted_positive,
            "positive_probability": latest_prediction.positive_probability,
        },
        "top_features": importances[:10],
    }

    model_uri = storage.write_bytes(serialize_pickle(model), model_path)
    metrics_uri = storage.write_text(json.dumps(metrics, indent=2), metrics_path)
    importance_uri = storage.write_dataframe_csv(pd.DataFrame(importances), importance_path)

    return {
        **metrics,
        "model_uri": model_uri,
        "metrics_uri": metrics_uri,
        "feature_importance_uri": importance_uri,
    }


def summarize_results(results: list[dict[str, object]], version: str, model_name: str, algorithm: str, window: str) -> dict[str, object]:
    trained = [result for result in results if result["status"] == "trained"]
    skipped = [result for result in results if result["status"] == "skipped"]
    return {
        "model_name": model_name,
        "algorithm": algorithm,
        "version": version,
        "window": window,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "asset_count": len(results),
        "trained_count": len(trained),
        "skipped_count": len(skipped),
        "results": results,
    }


def write_reports(storage: ObjectStorage, summary: dict[str, object], version: str, model_name: str) -> tuple[str, str]:
    report_dir = PurePosixPath("reports") / "model_training" / model_name
    history_path = report_dir / "history" / f"{version}.json"
    latest_path = report_dir / "latest.json"
    payload = json.dumps(summary, indent=2)
    history_uri = storage.write_text(payload, history_path)
    latest_uri = storage.write_text(payload, latest_path)
    return history_uri, latest_uri


def main() -> None:
    args = parse_args()
    as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date() if args.as_of else date.today()
    version = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    model_name = model_name_for_algorithm(args.algorithm)

    storage = get_object_storage(local_only=args.local_only)
    assets = select_assets(load_assets(), args.symbols, args.tier, args.market)
    if not assets:
        raise ValueError("No assets selected. Check --symbols, --tier, or --market.")

    metadata_store = None if args.skip_metadata else get_metadata_store()
    pipeline_run_id = metadata_store.start_pipeline_run("local_direction_model_training") if metadata_store else None

    results: list[dict[str, object]] = []
    try:
        for asset in assets:
            try:
                result = train_asset_model(
                    storage=storage,
                    asset=asset,
                    version=version,
                    model_name=model_name,
                    algorithm=args.algorithm,
                    window=args.window,
                    as_of=as_of,
                    min_train_rows=args.min_train_rows,
                    min_validation_rows=args.min_validation_rows,
                    min_test_rows=args.min_test_rows,
                )
            except Exception as exc:
                result = {
                    "symbol": asset.symbol,
                    "display_name": asset.display_name,
                    "market": asset.market,
                    "tier": asset.modeling_tier,
                    "window": args.window,
                    "status": "failed",
                    "reason": str(exc),
                }
            results.append(result)
            print(f"{result['symbol']}: {result['status']} {result.get('reason', '')}")

        summary = summarize_results(results, version, model_name, args.algorithm, args.window)
        history_uri, latest_uri = write_reports(storage, summary, version, model_name)

        if metadata_store and pipeline_run_id:
            for result in results:
                if result["status"] != "trained":
                    continue
                model_version_id = metadata_store.record_model_version(
                    pipeline_run_id=pipeline_run_id,
                    model_name=f"{model_name}:{result['symbol']}",
                    version=version,
                    tier=str(result["tier"]),
                    artifact_uri=str(result["model_uri"]),
                    train_row_count=int(result["train_row_count"]),
                    validation_row_count=int(result["validation_row_count"]),
                )
                metadata_store.record_model_metrics(
                    model_version_id,
                    "validation",
                    result["validation_metrics"],
                )
                metadata_store.record_model_metrics(
                    model_version_id,
                    "test",
                    result["test_metrics"],
                )
                metadata_store.record_model_metrics(
                    model_version_id,
                    "test_baseline_always_positive",
                    result["test_baselines"]["always_positive"],
                )
                metadata_store.record_model_metrics(
                    model_version_id,
                    "test_baseline_train_positive_rate",
                    result["test_baselines"]["train_positive_rate"],
                )
                metadata_store.record_model_metrics(
                    model_version_id,
                    "test_lift_vs_always_positive",
                    result["test_lift_vs_always_positive"],
                )
            metadata_store.record_dataset(
                pipeline_run_id=pipeline_run_id,
                dataset_type="model_training_report",
                storage_uri=latest_uri,
                row_count=len(results),
            )
            metadata_store.finish_pipeline_run(pipeline_run_id, "success")
    except Exception as exc:
        if metadata_store and pipeline_run_id:
            metadata_store.finish_pipeline_run(pipeline_run_id, "failed", str(exc))
        raise

    print(f"Storage: {storage}")
    print(f"Metadata: {'postgres' if metadata_store else 'disabled'}")
    print(f"Report: {latest_uri}")
    print(f"History: {history_uri}")
    print(f"Trained: {summary['trained_count']} / {summary['asset_count']}")


if __name__ == "__main__":
    main()
