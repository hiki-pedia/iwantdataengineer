"""Local Phase 1 market data ETL.

This script is intentionally simple. It proves the project can collect OHLCV
data, store raw files, build basic features, and store processed files before
Airflow, PostgreSQL metadata, and AWS are introduced.
"""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING

import pandas as pd

from chartmaster.config import Asset, get_postgres_dsn, load_assets
from chartmaster.data.market_provider import MarketDataRequest, YFinanceMarketDataProvider
from chartmaster.features.market_features import add_positive_5d_target, build_basic_market_features
from chartmaster.storage.local import (
    ObjectStorage,
    get_object_storage,
    relative_market_features_path,
    relative_market_raw_path,
)

if TYPE_CHECKING:
    from chartmaster.storage.postgres import PostgresMetadataStore


@dataclass(frozen=True)
class EtlResult:
    symbol: str
    raw_uri: str
    feature_uri: str
    fetched_rows: int
    raw_rows: int
    feature_rows: int


@dataclass(frozen=True)
class EtlFailure:
    symbol: str
    message: str


MARKET_COLUMNS = ["date", "open", "high", "low", "close", "adjusted_close", "volume"]


def select_assets(assets: list[Asset], symbols: list[str] | None, tier: str, market: str | None) -> list[Asset]:
    """Filter assets by explicit symbols or modeling tier."""
    if symbols:
        symbol_set = set(symbols)
        selected = [asset for asset in assets if asset.symbol in symbol_set]
    elif tier == "all":
        selected = assets
    else:
        selected = [asset for asset in assets if asset.modeling_tier == tier]

    if market:
        selected = [asset for asset in selected if asset.market == market]
    return selected


def normalize_market_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Normalize market data before merge/storage."""
    if dataframe.empty:
        return pd.DataFrame(columns=MARKET_COLUMNS)

    output = dataframe[MARKET_COLUMNS].copy()
    output["date"] = pd.to_datetime(output["date"]).dt.date
    output = output.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    return output.reset_index(drop=True)


def read_existing_market_data(storage: ObjectStorage, raw_relative_path) -> pd.DataFrame:
    """Read existing raw market data when present."""
    try:
        return normalize_market_dataframe(storage.read_dataframe_csv(raw_relative_path))
    except FileNotFoundError:
        return pd.DataFrame(columns=MARKET_COLUMNS)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
        if "No such file" in stderr or "No such file or directory" in stderr:
            return pd.DataFrame(columns=MARKET_COLUMNS)
        raise


def merge_market_data(existing: pd.DataFrame, fetched: pd.DataFrame) -> pd.DataFrame:
    """Merge fetched OHLCV rows into the existing historical dataset."""
    frames = [frame for frame in [existing, normalize_market_dataframe(fetched)] if not frame.empty]
    if not frames:
        return pd.DataFrame(columns=MARKET_COLUMNS)
    merged = pd.concat(frames, ignore_index=True)
    return normalize_market_dataframe(merged)


def get_metadata_store() -> PostgresMetadataStore | None:
    """Return metadata store when PostgreSQL is configured."""
    if not get_postgres_dsn():
        return None
    from chartmaster.storage.postgres import PostgresMetadataStore

    store = PostgresMetadataStore.from_env()
    store.init_schema()
    return store


def run_asset_etl(
    asset: Asset,
    start: date,
    end: date,
    storage: ObjectStorage,
    metadata_store: PostgresMetadataStore | None,
    pipeline_run_id: int | None,
    merge_existing: bool,
) -> EtlResult:
    """Collect and process one asset."""
    provider = YFinanceMarketDataProvider()
    request = MarketDataRequest(symbol=asset.symbol, start=start, end=end)
    fetched = provider.fetch_ohlcv(request)

    raw_relative_path = relative_market_raw_path("yfinance", asset.symbol)
    existing = read_existing_market_data(storage, raw_relative_path) if merge_existing else pd.DataFrame(columns=MARKET_COLUMNS)
    raw = merge_market_data(existing, fetched) if merge_existing else normalize_market_dataframe(fetched)

    if raw.empty:
        raise ValueError(f"No OHLCV data returned for {asset.symbol}")

    raw_uri = storage.write_dataframe_csv(raw, raw_relative_path)

    features = build_basic_market_features(raw)
    features = add_positive_5d_target(features)
    feature_relative_path = relative_market_features_path(asset.symbol)
    feature_uri = storage.write_dataframe_csv(features, feature_relative_path)

    if metadata_store and pipeline_run_id:
        metadata_store.record_dataset(
            pipeline_run_id=pipeline_run_id,
            dataset_type="raw_market_data",
            provider="yfinance",
            symbol=asset.symbol,
            storage_uri=raw_uri,
            row_count=len(raw),
            start_date=raw["date"].min(),
            end_date=raw["date"].max(),
        )
        metadata_store.record_dataset(
            pipeline_run_id=pipeline_run_id,
            dataset_type="processed_market_features",
            provider="yfinance",
            symbol=asset.symbol,
            storage_uri=feature_uri,
            row_count=len(features),
            start_date=features["date"].min(),
            end_date=features["date"].max(),
        )

    return EtlResult(
        symbol=asset.symbol,
        raw_uri=raw_uri,
        feature_uri=feature_uri,
        fetched_rows=len(fetched),
        raw_rows=len(raw),
        feature_rows=len(features),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local ChartMaster market data ETL.")
    parser.add_argument("--start", default="2024-01-01", help="Start date, YYYY-MM-DD.")
    parser.add_argument("--end", default=None, help="End date, YYYY-MM-DD. Defaults to today.")
    parser.add_argument(
        "--tier",
        choices=["core", "experimental", "all"],
        default="core",
        help="Asset tier to collect when --symbols is not provided.",
    )
    parser.add_argument(
        "--market",
        choices=["KR", "US"],
        default=None,
        help="Optional market filter used by scheduled Airflow DAGs.",
    )
    parser.add_argument(
        "--symbols",
        nargs="*",
        help="Optional explicit symbol list, e.g. 005930.KS MU.",
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
        "--fail-fast",
        action="store_true",
        help="Stop immediately when one asset fails.",
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Replace stored CSVs instead of merging fetched rows into existing history.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    start = datetime.strptime(args.start, "%Y-%m-%d").date()
    end = datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else date.today()
    storage = get_object_storage(local_only=args.local_only)

    asset_registry = load_assets()
    assets = select_assets(asset_registry, args.symbols, args.tier, args.market)
    if not assets:
        raise ValueError("No assets selected. Check --symbols or --tier.")

    metadata_store = None if args.skip_metadata else get_metadata_store()
    pipeline_run_id = metadata_store.start_pipeline_run("local_market_data_etl") if metadata_store else None
    if metadata_store:
        metadata_store.upsert_assets(asset_registry)

    print(f"Running local market data ETL for {len(assets)} assets.")
    print(f"Date range: {start} to {end}")
    print(f"Storage: {storage}")
    print(f"Metadata: {'postgres' if metadata_store else 'disabled'}")
    print(f"Mode: {'replace' if args.replace_existing else 'merge'}")

    results: list[EtlResult] = []
    failures: list[EtlFailure] = []
    try:
        for asset in assets:
            try:
                result = run_asset_etl(
                    asset,
                    start,
                    end,
                    storage,
                    metadata_store,
                    pipeline_run_id,
                    merge_existing=not args.replace_existing,
                )
                results.append(result)
                print(
                    f"{result.symbol}: fetched_rows={result.fetched_rows} "
                    f"raw_rows={result.raw_rows} raw={result.raw_uri} "
                    f"feature_rows={result.feature_rows} features={result.feature_uri}"
                )
            except Exception as exc:
                if args.fail_fast:
                    raise
                failure = EtlFailure(symbol=asset.symbol, message=str(exc))
                failures.append(failure)
                print(f"{failure.symbol}: failed={failure.message}")
    except Exception as exc:
        if metadata_store and pipeline_run_id:
            metadata_store.finish_pipeline_run(pipeline_run_id, "failed", str(exc))
        raise

    print(f"Completed local market data ETL for {len(results)} assets.")
    if failures:
        print(f"Failed assets: {len(failures)}")
        for failure in failures:
            print(f"- {failure.symbol}: {failure.message}")

    if metadata_store and pipeline_run_id:
        status = "success" if not failures else "partial_success"
        message = None if not failures else f"{len(failures)} assets failed"
        metadata_store.finish_pipeline_run(pipeline_run_id, status, message)


if __name__ == "__main__":
    main()
