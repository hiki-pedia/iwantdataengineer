from datetime import date

import pandas as pd

from chartmaster.features.market_features import add_positive_5d_target, build_basic_market_features
from chartmaster.quality.market_calendar import expected_market_sessions
from chartmaster.quality.market_data import validate_market_data


def make_raw(row_count: int = 30) -> pd.DataFrame:
    dates = pd.bdate_range("2026-07-01", periods=row_count)
    close = pd.Series(range(100, 100 + row_count), dtype="float64")
    return pd.DataFrame(
        {
            "date": dates.date,
            "open": close,
            "high": close + 2,
            "low": close - 2,
            "close": close + 1,
            "adjusted_close": close + 1,
            "volume": [0 if index == 5 else 1000 + index for index in range(row_count)],
        }
    )


def make_features(raw: pd.DataFrame) -> pd.DataFrame:
    return add_positive_5d_target(build_basic_market_features(raw))


def issue_codes(result) -> set[str]:
    return {issue.code for issue in result.issues}


def test_clean_dataset_passes_and_volume_change_has_no_infinity() -> None:
    raw = make_raw()
    features = make_features(raw)

    result = validate_market_data("TEST", raw, features, as_of=raw["date"].max())

    assert result.passed
    assert "infinite_feature_values" not in issue_codes(result)
    assert not features["volume_change_1d"].isin([float("inf"), float("-inf")]).any()


def test_duplicate_raw_date_fails() -> None:
    raw = pd.concat([make_raw(), make_raw().iloc[[0]]], ignore_index=True)
    features = make_features(raw)

    result = validate_market_data("TEST", raw, features, as_of=raw["date"].max())

    assert not result.passed
    assert "duplicate_raw_dates" in issue_codes(result)


def test_raw_feature_date_mismatch_fails() -> None:
    raw = make_raw()
    features = make_features(raw).iloc[:-1].copy()

    result = validate_market_data("TEST", raw, features, as_of=raw["date"].max())

    assert not result.passed
    assert "raw_feature_row_count_mismatch" in issue_codes(result)
    assert "raw_feature_date_mismatch" in issue_codes(result)


def test_provider_adjusted_close_and_ohlc_anomalies_are_warnings() -> None:
    raw = make_raw()
    raw.loc[0, "adjusted_close"] = 0
    raw.loc[1, "close"] = raw.loc[1, "high"] + 1
    features = make_features(raw)

    result = validate_market_data("TEST", raw, features, as_of=raw["date"].max())

    assert result.passed
    assert "non_positive_adjusted_close" in issue_codes(result)
    assert "inconsistent_ohlc" in issue_codes(result)


def test_stale_dataset_fails() -> None:
    raw = make_raw(5)
    features = make_features(raw)

    result = validate_market_data(
        "TEST",
        raw,
        features,
        as_of=date(2026, 8, 20),
        max_stale_calendar_days=7,
    )

    assert not result.passed
    assert "stale_raw_dataset" in issue_codes(result)


def test_krx_holiday_gap_is_not_missing_data() -> None:
    sessions = expected_market_sessions("KR", date(2017, 9, 29), date(2017, 10, 10))
    raw = make_raw(2)
    raw["date"] = [date(2017, 9, 29), date(2017, 10, 10)]
    features = make_features(raw)

    result = validate_market_data(
        "TEST",
        raw,
        features,
        as_of=date(2017, 10, 10),
        expected_sessions=sessions,
    )

    assert result.passed
    assert "missing_expected_sessions" not in issue_codes(result)


def test_missing_expected_exchange_session_warns() -> None:
    sessions = expected_market_sessions("KR", date(2026, 8, 17), date(2026, 8, 20))
    raw = make_raw(3)
    raw["date"] = [date(2026, 8, 17), date(2026, 8, 19), date(2026, 8, 20)]
    features = make_features(raw)

    result = validate_market_data(
        "TEST",
        raw,
        features,
        as_of=date(2026, 8, 20),
        expected_sessions=sessions,
    )

    assert result.passed
    assert "missing_expected_sessions" in issue_codes(result)
