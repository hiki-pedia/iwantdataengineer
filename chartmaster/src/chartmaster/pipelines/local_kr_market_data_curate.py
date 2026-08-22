"""Cross-check anomalous Korean rows and build canonical curated data."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import timedelta

import pandas as pd

from chartmaster.config import Asset, get_postgres_dsn, load_assets
from chartmaster.data.market_provider import MarketDataRequest, PykrxNaverMarketDataProvider
from chartmaster.features.market_features import add_positive_5d_target, build_basic_market_features
from chartmaster.pipelines.local_market_data_etl import (
    merge_market_data,
    normalize_market_dataframe,
    read_existing_market_data,
    select_assets,
)
from chartmaster.quality.curation import build_curated_market_data, inconsistent_ohlc_mask
from chartmaster.quality.market_calendar import expected_market_sessions
from chartmaster.storage.local import (
    ObjectStorage,
    get_object_storage,
    relative_market_curated_path,
    relative_market_features_path,
    relative_market_raw_path,
)
from chartmaster.storage.postgres import PostgresMetadataStore


@dataclass(frozen=True)
class CurateResult:
    symbol: str
    row_count: int
    replaced_row_count: int
    backfilled_row_count: int
    unresolved_missing_session_count: int
    invalid_adjusted_close_count: int
    curated_uri: str
    feature_uri: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build curated Korean market data.")
    parser.add_argument("--tier", choices=["core", "experimental", "all"], default="all")
    parser.add_argument("--symbols", nargs="*", help="Optional explicit Korean symbol list.")
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--skip-metadata", action="store_true")
    return parser.parse_args()


def get_metadata_store(enabled: bool) -> PostgresMetadataStore | None:
    if not enabled or not get_postgres_dsn():
        return None
    store = PostgresMetadataStore.from_env()
    store.init_schema()
    return store


SECONDARY_COVERAGE_START = pd.Timestamp("2014-01-01").date()


def fetch_secondary_for_issues(
    storage: ObjectStorage,
    asset: Asset,
    yfinance_raw: pd.DataFrame,
) -> pd.DataFrame:
    invalid_rows = yfinance_raw.loc[inconsistent_ohlc_mask(yfinance_raw)]
    actual_dates = set(yfinance_raw["date"])
    expected_sessions = expected_market_sessions("KR", min(actual_dates), max(actual_dates))
    missing_sessions = expected_sessions - actual_dates
    secondary_path = relative_market_raw_path("pykrx_naver", asset.symbol)
    existing = read_existing_market_data(storage, secondary_path)
    required_dates = set(invalid_rows["date"]) | {
        session for session in missing_sessions if session >= SECONDARY_COVERAGE_START
    }
    if not required_dates:
        return existing

    if required_dates.issubset(set(existing["date"])):
        return existing

    provider = PykrxNaverMarketDataProvider()
    request = MarketDataRequest(
        symbol=asset.symbol,
        start=min(required_dates),
        end=max(required_dates) + timedelta(days=1),
    )
    fetched = provider.fetch_ohlcv(request)
    secondary = merge_market_data(existing, fetched)
    storage.write_dataframe_csv(secondary, secondary_path)
    return secondary


def curate_asset(storage: ObjectStorage, asset: Asset) -> tuple[CurateResult, list[tuple]]:
    yfinance_path = relative_market_raw_path("yfinance", asset.symbol)
    yfinance_raw = normalize_market_dataframe(storage.read_dataframe_csv(yfinance_path))
    if yfinance_raw.empty:
        raise ValueError(f"No Yahoo raw data for {asset.symbol}")

    invalid_ohlc = inconsistent_ohlc_mask(yfinance_raw)
    invalid_adjusted = pd.to_numeric(yfinance_raw["adjusted_close"], errors="coerce") <= 0
    actual_dates = set(yfinance_raw["date"])
    expected_sessions = expected_market_sessions("KR", min(actual_dates), max(actual_dates))
    missing_sessions = expected_sessions - actual_dates
    secondary = fetch_secondary_for_issues(storage, asset, yfinance_raw)
    curated = build_curated_market_data(yfinance_raw, secondary, backfill_dates=missing_sessions)
    backfilled_dates = set(curated["date"]) - actual_dates
    unresolved_missing_sessions = missing_sessions - backfilled_dates
    curated_uri = storage.write_dataframe_csv(curated, relative_market_curated_path(asset.symbol))

    features = add_positive_5d_target(build_basic_market_features(curated))
    feature_uri = storage.write_dataframe_csv(features, relative_market_features_path(asset.symbol))

    issues: list[tuple] = []
    for observation_date in yfinance_raw.loc[invalid_adjusted, "date"]:
        issues.append(
            (
                asset.symbol,
                observation_date,
                "yfinance",
                "non_positive_adjusted_close",
                "warning",
                "open",
                "curated_adjusted_close_set_to_null",
            )
        )
    for observation_date in yfinance_raw.loc[invalid_ohlc, "date"]:
        issues.append(
            (
                asset.symbol,
                observation_date,
                "yfinance",
                "inconsistent_ohlc",
                "warning",
                "resolved",
                "curated_row_replaced_with_pykrx_naver",
            )
        )
    for observation_date in backfilled_dates:
        issues.append(
            (
                asset.symbol,
                observation_date,
                "yfinance",
                "missing_expected_session",
                "warning",
                "resolved",
                "curated_row_backfilled_with_pykrx_naver",
            )
        )
    for observation_date in unresolved_missing_sessions:
        issues.append(
            (
                asset.symbol,
                observation_date,
                "yfinance",
                "missing_expected_session",
                "warning",
                "open",
                "secondary_provider_has_no_row",
            )
        )

    return (
        CurateResult(
            symbol=asset.symbol,
            row_count=len(curated),
            replaced_row_count=int(invalid_ohlc.sum()),
            backfilled_row_count=len(backfilled_dates),
            unresolved_missing_session_count=len(unresolved_missing_sessions),
            invalid_adjusted_close_count=int(invalid_adjusted.sum()),
            curated_uri=curated_uri,
            feature_uri=feature_uri,
        ),
        issues,
    )


def main() -> None:
    args = parse_args()
    assets = select_assets(load_assets(), args.symbols, args.tier, "KR")
    if not assets:
        raise ValueError("No Korean assets selected.")

    storage = get_object_storage(local_only=args.local_only)
    metadata_store = get_metadata_store(not args.skip_metadata)
    pipeline_run_id = metadata_store.start_pipeline_run("local_kr_market_data_curate") if metadata_store else None
    results: list[CurateResult] = []
    failures: list[tuple[str, str]] = []

    for asset in assets:
        try:
            result, issues = curate_asset(storage, asset)
            print(
                f"{result.symbol}: rows={result.row_count} replaced={result.replaced_row_count} "
                f"backfilled={result.backfilled_row_count} unresolved_missing={result.unresolved_missing_session_count} "
                f"invalid_adjusted_close={result.invalid_adjusted_close_count} curated={result.curated_uri}"
            )
            if metadata_store and pipeline_run_id:
                metadata_store.record_dataset(
                    pipeline_run_id=pipeline_run_id,
                    dataset_type="curated_market_data",
                    provider="multi_source",
                    symbol=asset.symbol,
                    storage_uri=result.curated_uri,
                    row_count=result.row_count,
                )
                metadata_store.record_dataset(
                    pipeline_run_id=pipeline_run_id,
                    dataset_type="processed_market_features",
                    provider="curated",
                    symbol=asset.symbol,
                    storage_uri=result.feature_uri,
                    row_count=result.row_count,
                )
                metadata_store.record_quality_issues(pipeline_run_id, issues)
            results.append(result)
        except Exception as exc:
            failures.append((asset.symbol, str(exc)))
            print(f"{asset.symbol}: failed={exc}")

    if metadata_store and pipeline_run_id:
        status = "success" if not failures else "partial_success"
        message = None if not failures else f"{len(failures)} assets failed"
        metadata_store.finish_pipeline_run(pipeline_run_id, status, message)

    print(f"Summary: curated={len(results)} failed={len(failures)}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
