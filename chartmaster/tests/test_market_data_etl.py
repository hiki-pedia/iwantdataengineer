import pandas as pd

from chartmaster.pipelines.local_market_data_etl import merge_market_data, resolve_missing_block_start


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


def test_missing_block_start_expands_by_incomplete_recent_session_blocks() -> None:
    sessions = pd.bdate_range("2026-08-17", "2026-09-04").date
    existing_dates = [session for session in sessions if session <= pd.Timestamp("2026-08-26").date()]
    existing = pd.DataFrame(
        [[session, 10, 12, 9, 11, 11, 100] for session in existing_dates],
        columns=["date", "open", "high", "low", "close", "adjusted_close", "volume"],
    )

    start = resolve_missing_block_start(
        existing,
        requested_start=pd.Timestamp("2026-08-31").date(),
        end=pd.Timestamp("2026-09-05").date(),
        market="US",
        block_size=5,
        max_blocks=4,
    )

    assert start == pd.Timestamp("2026-08-24").date()


def test_missing_block_start_stops_when_recent_block_is_complete() -> None:
    sessions = pd.bdate_range("2026-08-31", "2026-09-04").date
    existing = pd.DataFrame(
        [[session, 10, 12, 9, 11, 11, 100] for session in sessions],
        columns=["date", "open", "high", "low", "close", "adjusted_close", "volume"],
    )

    start = resolve_missing_block_start(
        existing,
        requested_start=pd.Timestamp("2026-08-31").date(),
        end=pd.Timestamp("2026-09-05").date(),
        market="US",
        block_size=5,
        max_blocks=4,
    )

    assert start == pd.Timestamp("2026-08-31").date()
