"""Rebuild processed market features from stored raw data."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date

from chartmaster.config import Asset, get_postgres_dsn, load_assets
from chartmaster.features.market_features import add_positive_5d_target, build_basic_market_features
from chartmaster.pipelines.local_market_data_etl import normalize_market_dataframe, select_assets
from chartmaster.storage.local import (
    ObjectStorage,
    get_object_storage,
    relative_market_features_path,
    relative_market_raw_path,
)
from chartmaster.storage.postgres import PostgresMetadataStore


@dataclass(frozen=True)
class ReprocessResult:
    symbol: str
    row_count: int
    start_date: date
    end_date: date
    storage_uri: str | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild features from stored raw market data.")
    parser.add_argument("--tier", choices=["core", "experimental", "all"], default="all")
    parser.add_argument("--market", choices=["KR", "US"], default=None)
    parser.add_argument("--symbols", nargs="*", help="Optional explicit symbol list.")
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--skip-metadata", action="store_true")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write rebuilt features. Without this flag the command is a dry run.",
    )
    return parser.parse_args()


def rebuild_asset(storage: ObjectStorage, asset: Asset, write: bool) -> ReprocessResult:
    raw = storage.read_dataframe_csv(relative_market_raw_path("yfinance", asset.symbol))
    raw = normalize_market_dataframe(raw)
    if raw.empty:
        raise ValueError(f"No stored raw data for {asset.symbol}")

    features = add_positive_5d_target(build_basic_market_features(raw))
    storage_uri = None
    if write:
        storage_uri = storage.write_dataframe_csv(features, relative_market_features_path(asset.symbol))
    return ReprocessResult(
        symbol=asset.symbol,
        row_count=len(features),
        start_date=features["date"].min(),
        end_date=features["date"].max(),
        storage_uri=storage_uri,
    )


def get_metadata_store(enabled: bool) -> PostgresMetadataStore | None:
    if not enabled or not get_postgres_dsn():
        return None
    store = PostgresMetadataStore.from_env()
    store.init_schema()
    return store


def main() -> None:
    args = parse_args()
    storage = get_object_storage(local_only=args.local_only)
    assets = select_assets(load_assets(), args.symbols, args.tier, args.market)
    if not assets:
        raise ValueError("No assets selected. Check --symbols, --tier, or --market.")

    metadata_store = get_metadata_store(args.write and not args.skip_metadata)
    pipeline_run_id = metadata_store.start_pipeline_run("local_market_data_reprocess") if metadata_store else None
    results: list[ReprocessResult] = []
    failures: list[tuple[str, str]] = []

    for asset in assets:
        try:
            result = rebuild_asset(storage, asset, args.write)
            results.append(result)
            mode = result.storage_uri if args.write else "dry-run"
            print(f"{asset.symbol}: rows={result.row_count} output={mode}")
            if metadata_store and pipeline_run_id and result.storage_uri:
                metadata_store.record_dataset(
                    pipeline_run_id=pipeline_run_id,
                    dataset_type="reprocessed_market_features",
                    provider="yfinance",
                    symbol=asset.symbol,
                    storage_uri=result.storage_uri,
                    row_count=result.row_count,
                    start_date=result.start_date,
                    end_date=result.end_date,
                )
        except Exception as exc:
            failures.append((asset.symbol, str(exc)))
            print(f"{asset.symbol}: failed={exc}")

    if metadata_store and pipeline_run_id:
        status = "success" if not failures else "partial_success"
        message = None if not failures else f"{len(failures)} assets failed"
        metadata_store.finish_pipeline_run(pipeline_run_id, status, message)

    print(f"Mode: {'write' if args.write else 'dry-run'}")
    print(f"Summary: rebuilt={len(results)} failed={len(failures)}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
