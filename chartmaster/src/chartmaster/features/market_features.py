"""Market feature builders."""

import pandas as pd


def build_basic_market_features(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """Build the first OHLCV-based feature set."""
    features = ohlcv.sort_values("date").copy()
    features["turnover_value"] = features["close"] * features["volume"]
    features["return_1d"] = features["close"].pct_change(1, fill_method=None)
    features["return_5d"] = features["close"].pct_change(5, fill_method=None)
    features["return_20d"] = features["close"].pct_change(20, fill_method=None)
    volume_change = features["volume"].pct_change(1, fill_method=None)
    features["volume_change_1d"] = volume_change.replace([float("inf"), float("-inf")], float("nan"))
    features["moving_average_5"] = features["close"].rolling(5).mean()
    features["moving_average_20"] = features["close"].rolling(20).mean()
    features["volatility_5"] = features["return_1d"].rolling(5).std()
    features["volatility_20"] = features["return_1d"].rolling(20).std()
    return features


def add_positive_5d_target(features: pd.DataFrame) -> pd.DataFrame:
    """Add the initial binary classification target."""
    output = features.sort_values("date").copy()
    future_5d_return = output["close"].shift(-5) / output["close"] - 1
    output["future_5d_return"] = future_5d_return
    output["target_positive_5d_return"] = future_5d_return.gt(0).where(future_5d_return.notna())
    return output
