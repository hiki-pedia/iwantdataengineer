"""Run repeatable quality checks against stored ChartMaster market data."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import PurePosixPath

import pandas as pd

from chartmaster.config import Asset, load_assets
from chartmaster.pipelines.local_market_data_etl import select_assets
from chartmaster.quality.market_calendar import expected_market_sessions
from chartmaster.quality.market_data import AssetQualityResult, QualityIssue, validate_market_data
from chartmaster.storage.local import (
    ObjectStorage,
    get_object_storage,
    relative_market_curated_path,
    relative_market_features_path,
    relative_market_raw_path,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate stored ChartMaster market data.")
    parser.add_argument("--as-of", default=None, help="Quality-check date, YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--tier", choices=["core", "experimental", "all"], default="all")
    parser.add_argument("--market", choices=["KR", "US"], default=None)
    parser.add_argument("--symbols", nargs="*", help="Optional explicit symbol list.")
    parser.add_argument("--max-stale-calendar-days", type=int, default=7)
    parser.add_argument("--max-market-gap-days", type=int, default=7)
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--no-write-report", action="store_true")
    return parser.parse_args()


def missing_dataset_result(symbol: str, dataset_name: str, message: str) -> AssetQualityResult:
    return AssetQualityResult(
        symbol=symbol,
        raw_row_count=0,
        feature_row_count=0,
        start_date=None,
        end_date=None,
        issues=[QualityIssue("error", f"missing_{dataset_name}_dataset", message)],
    )


def validate_asset(
    storage: ObjectStorage,
    asset: Asset,
    as_of: date,
    max_stale_calendar_days: int,
    max_market_gap_days: int,
) -> AssetQualityResult:
    try:
        raw = storage.read_dataframe_csv(relative_market_raw_path("yfinance", asset.symbol))
    except Exception as exc:
        return missing_dataset_result(asset.symbol, "raw", str(exc))

    try:
        features = storage.read_dataframe_csv(relative_market_features_path(asset.symbol))
    except Exception as exc:
        return missing_dataset_result(asset.symbol, "feature", str(exc))

    canonical = raw
    if asset.market == "KR":
        try:
            canonical = storage.read_dataframe_csv(relative_market_curated_path(asset.symbol))
        except Exception:
            canonical = raw

    raw_dates = (
        pd.to_datetime(canonical["date"], errors="coerce").dropna()
        if "date" in canonical.columns
        else pd.Series(dtype="datetime64[ns]")
    )
    sessions = None
    if not raw_dates.empty:
        sessions = expected_market_sessions(asset.market, raw_dates.min().date(), as_of)

    return validate_market_data(
        symbol=asset.symbol,
        raw=canonical,
        features=features,
        as_of=as_of,
        max_stale_calendar_days=max_stale_calendar_days,
        max_market_gap_days=max_market_gap_days,
        expected_sessions=sessions,
    )


def build_report(results: list[AssetQualityResult], as_of: date, market: str | None) -> dict[str, object]:
    error_count = sum(issue.severity == "error" for result in results for issue in result.issues)
    warning_count = sum(issue.severity == "warning" for result in results for issue in result.issues)
    passed_assets = sum(result.passed for result in results)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "as_of": as_of.isoformat(),
        "market": market or "ALL",
        "summary": {
            "asset_count": len(results),
            "passed_asset_count": passed_assets,
            "failed_asset_count": len(results) - passed_assets,
            "error_count": error_count,
            "warning_count": warning_count,
        },
        "assets": [result.to_dict() for result in results],
    }


def report_paths(market: str | None, generated_at: str) -> tuple[PurePosixPath, PurePosixPath]:
    market_partition = f"market={market or 'ALL'}"
    run_id = generated_at.replace("-", "").replace(":", "").replace("+00:00", "Z").replace(".", "")
    report_dir = PurePosixPath("reports") / "data_quality" / market_partition
    return report_dir / "latest.json", report_dir / "history" / f"quality_{run_id}.json"


def main() -> None:
    args = parse_args()
    as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date() if args.as_of else date.today()
    storage = get_object_storage(local_only=args.local_only)
    assets = select_assets(load_assets(), args.symbols, args.tier, args.market)
    if not assets:
        raise ValueError("No assets selected. Check --symbols, --tier, or --market.")

    results = [
        validate_asset(
            storage,
            asset,
            as_of,
            args.max_stale_calendar_days,
            args.max_market_gap_days,
        )
        for asset in assets
    ]
    report = build_report(results, as_of, args.market)

    report_uri = "disabled"
    if not args.no_write_report:
        report_json = json.dumps(report, indent=2, ensure_ascii=True)
        latest_path, history_path = report_paths(args.market, str(report["generated_at"]))
        report_uri = storage.write_text(report_json, latest_path)
        storage.write_text(report_json, history_path)

    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(
            f"{result.symbol}: {status} raw_rows={result.raw_row_count} "
            f"feature_rows={result.feature_row_count} range={result.start_date}..{result.end_date}"
        )
        for issue in result.issues:
            print(f"  {issue.severity.upper()} {issue.code}: {issue.message} count={issue.count}")

    summary = report["summary"]
    print(
        f"Summary: assets={summary['asset_count']} passed={summary['passed_asset_count']} "
        f"failed={summary['failed_asset_count']} errors={summary['error_count']} "
        f"warnings={summary['warning_count']}"
    )
    print(f"Report: {report_uri}")

    if summary["failed_asset_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
