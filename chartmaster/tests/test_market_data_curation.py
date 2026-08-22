import pandas as pd

from chartmaster.quality.curation import build_curated_market_data


COLUMNS = ["date", "open", "high", "low", "close", "adjusted_close", "volume"]


def test_curated_data_replaces_complete_inconsistent_row() -> None:
    yahoo = pd.DataFrame(
        [["2024-10-14", 59500, 61200, 59400, 59300, 57535, 20886249]],
        columns=COLUMNS,
    )
    secondary = pd.DataFrame(
        [["2024-10-14", 59500, 61200, 59400, 60800, 60800, 20886249]],
        columns=COLUMNS,
    )

    curated = build_curated_market_data(yahoo, secondary)

    assert curated.loc[0, "close"] == 60800
    assert curated.loc[0, "source_provider"] == "pykrx_naver"
    assert curated.loc[0, "quality_status"] == "provider_replaced"


def test_curated_data_marks_invalid_adjusted_close_as_missing() -> None:
    yahoo = pd.DataFrame(
        [["2000-01-04", 100, 110, 90, 105, 0, 1000]],
        columns=COLUMNS,
    )

    curated = build_curated_market_data(yahoo, pd.DataFrame(columns=COLUMNS))

    assert pd.isna(curated.loc[0, "adjusted_close"])
    assert curated.loc[0, "quality_status"] == "adjusted_close_missing"


def test_curated_data_appends_only_requested_missing_sessions() -> None:
    yahoo = pd.DataFrame(
        [["2022-01-04", 100, 110, 90, 105, 105, 1000]],
        columns=COLUMNS,
    )
    secondary = pd.DataFrame(
        [
            ["2022-01-03", 95, 105, 90, 100, 100, 900],
            ["2022-01-05", 105, 115, 100, 110, 110, 1100],
        ],
        columns=COLUMNS,
    )

    curated = build_curated_market_data(
        yahoo,
        secondary,
        backfill_dates={pd.Timestamp("2022-01-03").date()},
    )

    assert curated["date"].astype(str).tolist() == ["2022-01-03", "2022-01-04"]
    assert curated.iloc[0]["quality_status"] == "provider_backfilled"
