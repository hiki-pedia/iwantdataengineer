"""Validation rules for raw OHLCV and processed market features."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Literal

import pandas as pd


RAW_COLUMNS = ["date", "open", "high", "low", "close", "adjusted_close", "volume"]
OHLC_COLUMNS = ["open", "high", "low", "close"]
PRICE_COLUMNS = OHLC_COLUMNS + ["adjusted_close"]
FEATURE_COLUMNS = [
    "turnover_value",
    "return_1d",
    "return_5d",
    "return_20d",
    "volume_change_1d",
    "moving_average_5",
    "moving_average_20",
    "volatility_5",
    "volatility_20",
    "future_5d_return",
    "target_positive_5d_return",
]


@dataclass(frozen=True)
class QualityIssue:
    severity: Literal["error", "warning"]
    code: str
    message: str
    count: int = 1


@dataclass(frozen=True)
class AssetQualityResult:
    symbol: str
    raw_row_count: int
    feature_row_count: int
    start_date: str | None
    end_date: str | None
    issues: list[QualityIssue]

    @property
    def passed(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["passed"] = self.passed
        return payload


def _issue(severity: Literal["error", "warning"], code: str, message: str, count: int = 1) -> QualityIssue:
    return QualityIssue(severity=severity, code=code, message=message, count=int(count))


def _normalized_dates(dataframe: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(dataframe["date"], errors="coerce").dt.date


def validate_market_data(
    symbol: str,
    raw: pd.DataFrame,
    features: pd.DataFrame,
    as_of: date,
    max_stale_calendar_days: int = 7,
    max_market_gap_days: int = 7,
    expected_sessions: set[date] | None = None,
) -> AssetQualityResult:
    """Validate one asset without modifying either dataframe."""
    issues: list[QualityIssue] = []
    start_date: str | None = None
    end_date: str | None = None

    missing_raw_columns = sorted(set(RAW_COLUMNS) - set(raw.columns))
    if missing_raw_columns:
        issues.append(
            _issue(
                "error",
                "missing_raw_columns",
                f"Missing raw columns: {', '.join(missing_raw_columns)}",
                len(missing_raw_columns),
            )
        )
    elif raw.empty:
        issues.append(_issue("error", "empty_raw_dataset", "Raw dataset has no rows."))
    else:
        raw_dates = _normalized_dates(raw)
        invalid_dates = int(raw_dates.isna().sum())
        if invalid_dates:
            issues.append(_issue("error", "invalid_raw_dates", "Raw dataset contains invalid dates.", invalid_dates))

        valid_dates = raw_dates.dropna()
        if not valid_dates.empty:
            minimum_date = valid_dates.min()
            maximum_date = valid_dates.max()
            start_date = minimum_date.isoformat()
            end_date = maximum_date.isoformat()
            duplicate_dates = int(valid_dates.duplicated().sum())
            if duplicate_dates:
                issues.append(_issue("error", "duplicate_raw_dates", "Raw dataset contains duplicate dates.", duplicate_dates))
            if not valid_dates.is_monotonic_increasing:
                issues.append(_issue("error", "unsorted_raw_dates", "Raw dates are not sorted in ascending order."))

            future_dates = int((valid_dates > as_of).sum())
            if future_dates:
                issues.append(_issue("error", "future_raw_dates", "Raw dataset contains dates after the quality-check date.", future_dates))

            if expected_sessions is not None:
                actual_date_set = set(valid_dates)
                covered_sessions = {
                    session for session in expected_sessions if minimum_date <= session <= maximum_date
                }
                missing_sessions = sorted(covered_sessions - actual_date_set)
                if missing_sessions:
                    examples = ", ".join(day.isoformat() for day in missing_sessions[:5])
                    issues.append(
                        _issue(
                            "warning",
                            "missing_expected_sessions",
                            f"Missing expected exchange sessions: {examples}",
                            len(missing_sessions),
                        )
                    )

                sessions_through_as_of = {session for session in expected_sessions if session <= as_of}
                if sessions_through_as_of:
                    latest_expected_session = max(sessions_through_as_of)
                    missing_recent_sessions = {
                        session for session in sessions_through_as_of if session > maximum_date
                    }
                    if missing_recent_sessions:
                        issues.append(
                            _issue(
                                "error",
                                "missing_latest_market_session",
                                f"Latest expected session is {latest_expected_session.isoformat()}, "
                                f"but latest raw row is {maximum_date.isoformat()}.",
                                len(missing_recent_sessions),
                            )
                        )
            else:
                stale_days = (as_of - maximum_date).days
                if stale_days > max_stale_calendar_days:
                    issues.append(
                        _issue(
                            "error",
                            "stale_raw_dataset",
                            f"Latest raw row is {stale_days} calendar days old; threshold is {max_stale_calendar_days}.",
                        )
                    )

                date_gaps = pd.to_datetime(valid_dates).sort_values().diff().dt.days
                long_gaps = int((date_gaps > max_market_gap_days).sum())
                if long_gaps:
                    issues.append(
                        _issue(
                            "warning",
                            "long_market_date_gaps",
                            f"Found gaps longer than {max_market_gap_days} calendar days; verify source coverage.",
                            long_gaps,
                        )
                    )

        numeric_raw = raw[PRICE_COLUMNS + ["volume"]].apply(pd.to_numeric, errors="coerce")
        invalid_numeric = int(numeric_raw[OHLC_COLUMNS + ["volume"]].isna().sum().sum())
        if invalid_numeric:
            issues.append(_issue("error", "invalid_raw_numeric_values", "Raw OHLC and volume contain null or non-numeric values.", invalid_numeric))

        non_positive_prices = int((numeric_raw[OHLC_COLUMNS] <= 0).sum().sum())
        if non_positive_prices:
            issues.append(_issue("error", "non_positive_ohlc", "Raw OHLC columns contain zero or negative values.", non_positive_prices))

        invalid_adjusted_close = int((numeric_raw["adjusted_close"].isna() | (numeric_raw["adjusted_close"] <= 0)).sum())
        if invalid_adjusted_close:
            issues.append(
                _issue(
                    "warning",
                    "non_positive_adjusted_close",
                    "Adjusted close is missing, zero, or negative; retain raw data and verify with another provider.",
                    invalid_adjusted_close,
                )
            )

        negative_volume = int((numeric_raw["volume"] < 0).sum())
        if negative_volume:
            issues.append(_issue("error", "negative_volume", "Raw volume contains negative values.", negative_volume))

        valid_ohlc = numeric_raw[OHLC_COLUMNS].dropna()
        invalid_high = valid_ohlc["high"] < valid_ohlc[["open", "low", "close"]].max(axis=1)
        invalid_low = valid_ohlc["low"] > valid_ohlc[["open", "high", "close"]].min(axis=1)
        inconsistent_ohlc = int((invalid_high | invalid_low).sum())
        if inconsistent_ohlc:
            issues.append(
                _issue(
                    "warning",
                    "inconsistent_ohlc",
                    "Provider rows violate OHLC high/low relationships; retain raw data and cross-check before repair.",
                    inconsistent_ohlc,
                )
            )

    required_feature_columns = RAW_COLUMNS + FEATURE_COLUMNS
    missing_feature_columns = sorted(set(required_feature_columns) - set(features.columns))
    if missing_feature_columns:
        issues.append(
            _issue(
                "error",
                "missing_feature_columns",
                f"Missing feature columns: {', '.join(missing_feature_columns)}",
                len(missing_feature_columns),
            )
        )
    elif features.empty:
        issues.append(_issue("error", "empty_feature_dataset", "Feature dataset has no rows."))
    else:
        feature_dates = _normalized_dates(features)
        invalid_feature_dates = int(feature_dates.isna().sum())
        if invalid_feature_dates:
            issues.append(
                _issue("error", "invalid_feature_dates", "Feature dataset contains invalid dates.", invalid_feature_dates)
            )

        duplicate_feature_dates = int(feature_dates.dropna().duplicated().sum())
        if duplicate_feature_dates:
            issues.append(
                _issue("error", "duplicate_feature_dates", "Feature dataset contains duplicate dates.", duplicate_feature_dates)
            )

        numeric_features = features[FEATURE_COLUMNS[:-1]].apply(pd.to_numeric, errors="coerce")
        infinite_features = int(((numeric_features == float("inf")) | (numeric_features == float("-inf"))).sum().sum())
        if infinite_features:
            issues.append(
                _issue("error", "infinite_feature_values", "Feature columns contain positive or negative infinity.", infinite_features)
            )

        if not missing_raw_columns and not raw.empty:
            raw_dates = _normalized_dates(raw)
            raw_date_set = set(raw_dates.dropna())
            feature_date_set = set(feature_dates.dropna())
            if len(raw) != len(features):
                issues.append(
                    _issue(
                        "error",
                        "raw_feature_row_count_mismatch",
                        f"Raw rows ({len(raw)}) and feature rows ({len(features)}) differ.",
                        abs(len(raw) - len(features)),
                    )
                )
            missing_feature_dates = len(raw_date_set - feature_date_set)
            extra_feature_dates = len(feature_date_set - raw_date_set)
            if missing_feature_dates or extra_feature_dates:
                issues.append(
                    _issue(
                        "error",
                        "raw_feature_date_mismatch",
                        "Raw and feature datasets do not cover the same dates.",
                        missing_feature_dates + extra_feature_dates,
                    )
                )

    return AssetQualityResult(
        symbol=symbol,
        raw_row_count=len(raw),
        feature_row_count=len(features),
        start_date=start_date,
        end_date=end_date,
        issues=issues,
    )
