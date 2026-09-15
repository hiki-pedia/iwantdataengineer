from datetime import date

import pandas as pd

from chartmaster.models.modeling_dataset import (
    apply_window,
    classify_eligibility,
    split_by_fixed_dates,
    summarize_asset_window,
)


FEATURE_COLUMNS = ["return_1d", "rsi_14"]
TARGET_COLUMN = "target_positive_5d_return"


def make_dataset(start: str = "2019-01-01", periods: int = 2000) -> pd.DataFrame:
    dates = pd.bdate_range(start, periods=periods)
    return pd.DataFrame(
        {
            "date": dates,
            "return_1d": [0.01 if index % 2 == 0 else -0.01 for index in range(periods)],
            "rsi_14": [45 + (index % 20) for index in range(periods)],
            TARGET_COLUMN: [index % 2 == 0 for index in range(periods)],
        }
    )


def test_window_filters_post_2020_and_recent_5y() -> None:
    dataset = make_dataset("2018-01-01", 2500)

    post_2020 = apply_window(dataset, "post_2020", date(2026, 8, 23))
    recent_5y = apply_window(dataset, "recent_5y", date(2026, 8, 23))

    assert post_2020["date"].min().date() >= date(2020, 1, 1)
    assert recent_5y["date"].min().date() >= date(2021, 8, 24)


def test_fixed_date_split_uses_future_as_test() -> None:
    dataset = make_dataset("2023-01-01", 900)
    splits = split_by_fixed_dates(dataset)

    assert splits["train"]["date"].max().date() <= date(2023, 12, 31)
    assert splits["validation"]["date"].min().date() >= date(2024, 1, 1)
    assert splits["validation"]["date"].max().date() <= date(2025, 12, 31)
    assert splits["test"]["date"].min().date() >= date(2026, 1, 1)


def test_eligibility_requires_minimum_rows_and_both_classes() -> None:
    dataset = make_dataset("2020-01-01", 1700)
    splits = split_by_fixed_dates(dataset)

    eligibility, reason = classify_eligibility(splits, TARGET_COLUMN)

    assert eligibility == "core_trainable"
    assert reason is None


def test_eligibility_rejects_short_recent_dataset() -> None:
    dataset = make_dataset("2026-06-01", 40)
    splits = split_by_fixed_dates(dataset)

    eligibility, reason = classify_eligibility(splits, TARGET_COLUMN)

    assert eligibility == "experimental_observation"
    assert "train rows" in str(reason)


def test_asset_window_summary_reports_missing_feature_ratio() -> None:
    dataset = make_dataset("2020-01-01", 1700)
    dataset.loc[:99, "rsi_14"] = None

    summary = summarize_asset_window(
        dataframe=dataset,
        symbol="TEST",
        display_name="Test",
        market="KR",
        tier="core",
        window="all_history",
        as_of=date(2026, 8, 23),
        feature_columns=FEATURE_COLUMNS,
        target_column=TARGET_COLUMN,
    )

    assert summary.eligibility == "core_trainable"
    assert summary.missing_feature_ratio > 0
    assert {split.name for split in summary.splits} == {"train", "validation", "test"}
