"""Market feature builders."""

import pandas as pd


def _without_infinity(series: pd.Series) -> pd.Series:
    """Return a numeric series where infinite values are treated as missing."""
    return series.replace([float("inf"), float("-inf")], float("nan"))


def build_basic_market_features(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """Build the first OHLCV-based feature set."""
    features = ohlcv.sort_values("date").copy()
    close = pd.to_numeric(features["close"], errors="coerce")
    high = pd.to_numeric(features["high"], errors="coerce")
    low = pd.to_numeric(features["low"], errors="coerce")
    volume = pd.to_numeric(features["volume"], errors="coerce")

    features["turnover_value"] = features["close"] * features["volume"]
    features["return_1d"] = close.pct_change(1, fill_method=None)
    features["return_5d"] = close.pct_change(5, fill_method=None)
    features["return_20d"] = close.pct_change(20, fill_method=None)
    features["return_60d"] = close.pct_change(60, fill_method=None)
    features["volume_change_1d"] = _without_infinity(volume.pct_change(1, fill_method=None))

    features["moving_average_5"] = close.rolling(5).mean()
    features["moving_average_20"] = close.rolling(20).mean()
    features["moving_average_60"] = close.rolling(60).mean()
    features["moving_average_120"] = close.rolling(120).mean()
    features["ema_12"] = close.ewm(span=12, adjust=False).mean()
    features["ema_26"] = close.ewm(span=26, adjust=False).mean()

    features["volatility_5"] = features["return_1d"].rolling(5).std()
    features["volatility_20"] = features["return_1d"].rolling(20).std()
    features["volatility_60"] = features["return_1d"].rolling(60).std()

    features["price_to_ma20"] = _without_infinity(close / features["moving_average_20"] - 1)
    features["price_to_ma60"] = _without_infinity(close / features["moving_average_60"] - 1)

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = _without_infinity(gain / loss)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.mask((loss == 0) & (gain > 0), 100)
    rsi = rsi.mask((loss == 0) & (gain == 0), 50)
    features["rsi_14"] = rsi

    features["macd"] = features["ema_12"] - features["ema_26"]
    features["macd_signal"] = features["macd"].ewm(span=9, adjust=False).mean()
    features["macd_histogram"] = features["macd"] - features["macd_signal"]

    bollinger_middle = close.rolling(20).mean()
    bollinger_std = close.rolling(20).std()
    features["bollinger_middle_20"] = bollinger_middle
    features["bollinger_upper_20"] = bollinger_middle + (bollinger_std * 2)
    features["bollinger_lower_20"] = bollinger_middle - (bollinger_std * 2)
    bollinger_width = features["bollinger_upper_20"] - features["bollinger_lower_20"]
    features["bollinger_percent_b_20"] = _without_infinity((close - features["bollinger_lower_20"]) / bollinger_width)
    features["bollinger_bandwidth_20"] = _without_infinity(bollinger_width / bollinger_middle)
    features["close_zscore_20"] = _without_infinity((close - bollinger_middle) / bollinger_std)

    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    features["true_range"] = true_range
    features["atr_14"] = true_range.rolling(14).mean()

    features["momentum_10"] = close - close.shift(10)
    features["momentum_20"] = close - close.shift(20)
    features["volume_average_20"] = volume.rolling(20).mean()
    features["volume_ratio_20"] = _without_infinity(volume / features["volume_average_20"])

    features["rolling_high_20"] = high.rolling(20).max()
    features["rolling_low_20"] = low.rolling(20).min()
    features["rolling_high_60"] = high.rolling(60).max()
    features["rolling_low_60"] = low.rolling(60).min()
    features["breakout_high_20"] = close.gt(features["rolling_high_20"].shift(1))
    features["breakdown_low_20"] = close.lt(features["rolling_low_20"].shift(1))
    features["breakout_high_60"] = close.gt(features["rolling_high_60"].shift(1))
    features["breakdown_low_60"] = close.lt(features["rolling_low_60"].shift(1))
    return features


def add_positive_5d_target(features: pd.DataFrame) -> pd.DataFrame:
    """Add the initial binary classification target."""
    output = features.sort_values("date").copy()
    future_5d_return = output["close"].shift(-5) / output["close"] - 1
    output["future_5d_return"] = future_5d_return
    output["target_positive_5d_return"] = future_5d_return.gt(0).where(future_5d_return.notna())
    return output
