import pandas as pd

from chartmaster.features.market_features import build_basic_market_features


def make_raw(row_count: int = 160) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-01", periods=row_count)
    close = pd.Series(range(100, 100 + row_count), dtype="float64")
    return pd.DataFrame(
        {
            "date": dates.date,
            "open": close - 1,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "adjusted_close": close,
            "volume": [0 if index == 5 else 1000 + index for index in range(row_count)],
        }
    )


def test_technical_indicator_columns_are_created() -> None:
    features = build_basic_market_features(make_raw())

    expected_columns = {
        "return_60d",
        "moving_average_60",
        "moving_average_120",
        "ema_12",
        "ema_26",
        "price_to_ma20",
        "price_to_ma60",
        "rsi_14",
        "macd",
        "macd_signal",
        "macd_histogram",
        "bollinger_middle_20",
        "bollinger_upper_20",
        "bollinger_lower_20",
        "bollinger_percent_b_20",
        "bollinger_bandwidth_20",
        "close_zscore_20",
        "true_range",
        "atr_14",
        "momentum_10",
        "momentum_20",
        "volume_average_20",
        "volume_ratio_20",
        "rolling_high_20",
        "rolling_low_20",
        "rolling_high_60",
        "rolling_low_60",
        "breakout_high_20",
        "breakdown_low_20",
        "breakout_high_60",
        "breakdown_low_60",
    }

    assert expected_columns.issubset(features.columns)


def test_technical_indicators_do_not_create_infinity() -> None:
    raw = make_raw()
    raw.loc[20:30, "close"] = 120
    raw.loc[20:30, "open"] = 120
    raw.loc[20:30, "high"] = 120
    raw.loc[20:30, "low"] = 120
    raw.loc[20:30, "volume"] = 0

    features = build_basic_market_features(raw)
    numeric = features.select_dtypes(include=["number"])

    assert not numeric.isin([float("inf"), float("-inf")]).any().any()


def test_rsi_for_strict_uptrend_reaches_overbought_value() -> None:
    features = build_basic_market_features(make_raw())

    assert features["rsi_14"].dropna().iloc[-1] == 100


def test_breakout_signal_uses_previous_rolling_high() -> None:
    raw = make_raw(70)
    raw.loc[65, "close"] = raw.loc[:64, "high"].max() + 10
    raw.loc[65, "high"] = raw.loc[65, "close"] + 1
    raw.loc[65, "open"] = raw.loc[65, "close"] - 1
    raw.loc[65, "low"] = raw.loc[65, "close"] - 2

    features = build_basic_market_features(raw)

    assert bool(features.loc[65, "breakout_high_20"])
