"""Modeling dataset windowing and split helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

import pandas as pd


WindowName = Literal["all_history", "post_2020", "recent_5y"]
SplitName = Literal["train", "validation", "test"]
Eligibility = Literal["core_trainable", "experimental_observation"]

WINDOWS: tuple[WindowName, ...] = ("all_history", "post_2020", "recent_5y")
SPLITS: tuple[SplitName, ...] = ("train", "validation", "test")
TRAIN_END = date(2023, 12, 31)
VALIDATION_START = date(2024, 1, 1)
VALIDATION_END = date(2025, 12, 31)
TEST_START = date(2026, 1, 1)
MIN_TRAIN_ROWS = 500
MIN_VALIDATION_ROWS = 100
MIN_TEST_ROWS = 20


@dataclass(frozen=True)
class SplitSummary:
    name: SplitName
    row_count: int
    start_date: str | None
    end_date: str | None
    positive_ratio: float | None
    has_both_classes: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "row_count": self.row_count,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "positive_ratio": self.positive_ratio,
            "has_both_classes": self.has_both_classes,
        }


@dataclass(frozen=True)
class AssetWindowSummary:
    symbol: str
    display_name: str
    market: str
    tier: str
    window: WindowName
    eligibility: Eligibility
    row_count: int
    start_date: str | None
    end_date: str | None
    positive_ratio: float | None
    missing_feature_ratio: float
    splits: list[SplitSummary]
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "display_name": self.display_name,
            "market": self.market,
            "tier": self.tier,
            "window": self.window,
            "eligibility": self.eligibility,
            "row_count": self.row_count,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "positive_ratio": self.positive_ratio,
            "missing_feature_ratio": self.missing_feature_ratio,
            "splits": [split.to_dict() for split in self.splits],
            "reason": self.reason,
        }


def window_start_date(window: WindowName, as_of: date) -> date | None:
    if window == "all_history":
        return None
    if window == "post_2020":
        return date(2020, 1, 1)
    if window == "recent_5y":
        return as_of - timedelta(days=365 * 5)
    raise ValueError(f"Unknown window: {window}")


def apply_window(dataframe: pd.DataFrame, window: WindowName, as_of: date) -> pd.DataFrame:
    output = dataframe.copy()
    output["date"] = pd.to_datetime(output["date"])
    start = window_start_date(window, as_of)
    if start is not None:
        output = output[output["date"].dt.date >= start]
    return output.sort_values("date").reset_index(drop=True)


def split_by_fixed_dates(dataframe: pd.DataFrame) -> dict[SplitName, pd.DataFrame]:
    dates = pd.to_datetime(dataframe["date"]).dt.date
    return {
        "train": dataframe[dates <= TRAIN_END].copy(),
        "validation": dataframe[(dates >= VALIDATION_START) & (dates <= VALIDATION_END)].copy(),
        "test": dataframe[dates >= TEST_START].copy(),
    }


def positive_ratio(dataframe: pd.DataFrame, target_column: str) -> float | None:
    if dataframe.empty or target_column not in dataframe:
        return None
    target = dataframe[target_column].dropna().astype(bool)
    if target.empty:
        return None
    return float(target.mean())


def has_both_classes(dataframe: pd.DataFrame, target_column: str) -> bool:
    if dataframe.empty or target_column not in dataframe:
        return False
    target = dataframe[target_column].dropna().astype(bool)
    return target.nunique() == 2


def date_range(dataframe: pd.DataFrame) -> tuple[str | None, str | None]:
    if dataframe.empty:
        return None, None
    dates = pd.to_datetime(dataframe["date"])
    return dates.min().date().isoformat(), dates.max().date().isoformat()


def missing_feature_ratio(dataframe: pd.DataFrame, feature_columns: list[str]) -> float:
    if dataframe.empty or not feature_columns:
        return 0.0
    available_columns = [column for column in feature_columns if column in dataframe.columns]
    if not available_columns:
        return 1.0
    missing = dataframe[available_columns].isna().sum().sum()
    total = len(dataframe) * len(available_columns)
    return float(missing / total) if total else 0.0


def split_summary(name: SplitName, dataframe: pd.DataFrame, target_column: str) -> SplitSummary:
    start_date, end_date = date_range(dataframe)
    return SplitSummary(
        name=name,
        row_count=len(dataframe),
        start_date=start_date,
        end_date=end_date,
        positive_ratio=positive_ratio(dataframe, target_column),
        has_both_classes=has_both_classes(dataframe, target_column),
    )


def classify_eligibility(splits: dict[SplitName, pd.DataFrame], target_column: str) -> tuple[Eligibility, str | None]:
    train_rows = len(splits["train"])
    validation_rows = len(splits["validation"])
    test_rows = len(splits["test"])
    if train_rows < MIN_TRAIN_ROWS:
        return "experimental_observation", f"train rows {train_rows} < {MIN_TRAIN_ROWS}"
    if validation_rows < MIN_VALIDATION_ROWS:
        return "experimental_observation", f"validation rows {validation_rows} < {MIN_VALIDATION_ROWS}"
    if test_rows < MIN_TEST_ROWS:
        return "experimental_observation", f"test rows {test_rows} < {MIN_TEST_ROWS}"
    for split_name in SPLITS:
        if not has_both_classes(splits[split_name], target_column):
            return "experimental_observation", f"{split_name} split does not contain both target classes"
    return "core_trainable", None


def summarize_asset_window(
    *,
    dataframe: pd.DataFrame,
    symbol: str,
    display_name: str,
    market: str,
    tier: str,
    window: WindowName,
    as_of: date,
    feature_columns: list[str],
    target_column: str,
) -> AssetWindowSummary:
    windowed = apply_window(dataframe, window, as_of)
    splits = split_by_fixed_dates(windowed)
    eligibility, reason = classify_eligibility(splits, target_column)
    start_date, end_date = date_range(windowed)
    return AssetWindowSummary(
        symbol=symbol,
        display_name=display_name,
        market=market,
        tier=tier,
        window=window,
        eligibility=eligibility,
        row_count=len(windowed),
        start_date=start_date,
        end_date=end_date,
        positive_ratio=positive_ratio(windowed, target_column),
        missing_feature_ratio=missing_feature_ratio(windowed, feature_columns),
        splits=[split_summary(name, splits[name], target_column) for name in SPLITS],
        reason=reason,
    )
