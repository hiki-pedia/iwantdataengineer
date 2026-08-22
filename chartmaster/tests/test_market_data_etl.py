import pandas as pd

from chartmaster.pipelines.local_market_data_etl import merge_market_data


def test_overlap_merge_is_idempotent_and_keeps_latest_row() -> None:
    existing = pd.DataFrame(
        [
            ["2026-08-18", 10, 12, 9, 11, 11, 100],
            ["2026-08-19", 11, 13, 10, 12, 12, 110],
        ],
        columns=["date", "open", "high", "low", "close", "adjusted_close", "volume"],
    )
    fetched = pd.DataFrame(
        [
            ["2026-08-19", 11, 14, 10, 13, 13, 120],
            ["2026-08-20", 13, 15, 12, 14, 14, 130],
        ],
        columns=existing.columns,
    )

    merged_once = merge_market_data(existing, fetched)
    merged_twice = merge_market_data(merged_once, fetched)

    assert len(merged_once) == 3
    assert len(merged_twice) == 3
    assert merged_twice["date"].is_unique
    assert merged_twice.loc[merged_twice["date"].astype(str) == "2026-08-19", "close"].item() == 13
