"""Build Phase 7 modeling dataset summaries from processed feature files."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import PurePosixPath

from chartmaster.config import load_assets
from chartmaster.models.baseline import TARGET_COLUMN
from chartmaster.models.modeling_dataset import WINDOWS, summarize_asset_window
from chartmaster.pipelines.local_market_data_etl import select_assets
from chartmaster.storage.local import get_object_storage, relative_market_features_path


CHART_SIGNAL_FEATURE_COLUMNS = [
    "turnover_value",
    "return_1d",
    "return_5d",
    "return_20d",
    "return_60d",
    "volume_change_1d",
    "moving_average_5",
    "moving_average_20",
    "moving_average_60",
    "moving_average_120",
    "ema_12",
    "ema_26",
    "price_to_ma20",
    "price_to_ma60",
    "volatility_5",
    "volatility_20",
    "volatility_60",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_histogram",
    "bollinger_percent_b_20",
    "bollinger_bandwidth_20",
    "close_zscore_20",
    "atr_14",
    "momentum_10",
    "momentum_20",
    "volume_ratio_20",
    "breakout_high_20",
    "breakdown_low_20",
    "breakout_high_60",
    "breakdown_low_60",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize modeling dataset windows and splits.")
    parser.add_argument("--as-of", default=None, help="Summary date, YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--tier", choices=["core", "experimental", "all"], default="all")
    parser.add_argument("--market", choices=["KR", "US"], default=None)
    parser.add_argument("--symbols", nargs="*", help="Optional explicit symbol list.")
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--no-write-report", action="store_true")
    return parser.parse_args()


def report_paths(generated_at: str) -> tuple[PurePosixPath, PurePosixPath]:
    run_id = generated_at.replace("-", "").replace(":", "").replace("+00:00", "Z").replace(".", "")
    report_dir = PurePosixPath("reports") / "modeling_dataset_summary"
    return report_dir / "latest.json", report_dir / "history" / f"summary_{run_id}.json"


def main() -> None:
    args = parse_args()
    as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date() if args.as_of else date.today()
    storage = get_object_storage(local_only=args.local_only)
    assets = select_assets(load_assets(), args.symbols, args.tier, args.market)
    if not assets:
        raise ValueError("No assets selected. Check --symbols, --tier, or --market.")

    asset_windows = []
    skipped_assets = []
    for asset in assets:
        try:
            dataframe = storage.read_dataframe_csv(relative_market_features_path(asset.symbol))
        except Exception as exc:
            skipped_assets.append({"symbol": asset.symbol, "reason": str(exc)})
            continue
        for window in WINDOWS:
            asset_windows.append(
                summarize_asset_window(
                    dataframe=dataframe,
                    symbol=asset.symbol,
                    display_name=asset.display_name,
                    market=asset.market,
                    tier=asset.modeling_tier,
                    window=window,
                    as_of=as_of,
                    feature_columns=CHART_SIGNAL_FEATURE_COLUMNS,
                    target_column=TARGET_COLUMN,
                )
            )

    generated_at = datetime.now(timezone.utc).isoformat()
    summary = {
        "generated_at": generated_at,
        "as_of": as_of.isoformat(),
        "feature_set": "chart_signal_v1",
        "target_column": TARGET_COLUMN,
        "feature_columns": CHART_SIGNAL_FEATURE_COLUMNS,
        "window_names": list(WINDOWS),
        "split_policy": {
            "train": "<= 2023-12-31",
            "validation": "2024-01-01..2025-12-31",
            "test": ">= 2026-01-01",
        },
        "eligibility_policy": {
            "train_min_rows": 500,
            "validation_min_rows": 100,
            "test_min_rows": 20,
            "requires_both_classes_per_split": True,
        },
        "summary": {
            "asset_count": len(assets),
            "asset_window_count": len(asset_windows),
            "core_trainable_count": sum(item.eligibility == "core_trainable" for item in asset_windows),
            "experimental_observation_count": sum(
                item.eligibility == "experimental_observation" for item in asset_windows
            ),
            "skipped_asset_count": len(skipped_assets),
        },
        "asset_windows": [item.to_dict() for item in asset_windows],
        "skipped_assets": skipped_assets,
    }

    report_uri = "disabled"
    if not args.no_write_report:
        payload = json.dumps(summary, indent=2, ensure_ascii=True)
        latest_path, history_path = report_paths(generated_at)
        report_uri = storage.write_text(payload, latest_path)
        storage.write_text(payload, history_path)

    print(
        f"Summary: assets={summary['summary']['asset_count']} "
        f"asset_windows={summary['summary']['asset_window_count']} "
        f"core_trainable={summary['summary']['core_trainable_count']} "
        f"experimental_observation={summary['summary']['experimental_observation_count']} "
        f"skipped={summary['summary']['skipped_asset_count']}"
    )
    for window in WINDOWS:
        count = sum(item.window == window and item.eligibility == "core_trainable" for item in asset_windows)
        print(f"{window}: core_trainable={count}")
    print(f"Report: {report_uri}")


if __name__ == "__main__":
    main()
