"""Build canonical market rows while preserving source-level raw data."""

from __future__ import annotations

import pandas as pd

from chartmaster.pipelines.local_market_data_etl import normalize_market_dataframe


OHLC_COLUMNS = ["open", "high", "low", "close"]
REPLACEMENT_COLUMNS = OHLC_COLUMNS + ["adjusted_close", "volume"]


def inconsistent_ohlc_mask(dataframe: pd.DataFrame) -> pd.Series:
    """Return rows whose close/open values fall outside the daily high-low range."""
    ohlc = dataframe[OHLC_COLUMNS].apply(pd.to_numeric, errors="coerce")
    return (ohlc["high"] < ohlc[["open", "low", "close"]].max(axis=1)) | (
        ohlc["low"] > ohlc[["open", "high", "close"]].min(axis=1)
    )


def build_curated_market_data(
    yfinance_raw: pd.DataFrame,
    secondary_raw: pd.DataFrame,
    backfill_dates: set | None = None,
) -> pd.DataFrame:
    """Create canonical rows and replace only proven inconsistent Yahoo rows."""
    curated = normalize_market_dataframe(yfinance_raw)
    curated["source_provider"] = "yfinance"
    curated["quality_status"] = "valid"

    invalid_adjusted = pd.to_numeric(curated["adjusted_close"], errors="coerce") <= 0
    curated.loc[invalid_adjusted, "adjusted_close"] = float("nan")
    curated.loc[invalid_adjusted, "quality_status"] = "adjusted_close_missing"

    secondary = normalize_market_dataframe(secondary_raw).set_index("date")
    requested_backfills = backfill_dates or set()
    available_backfills = sorted(requested_backfills & (set(secondary.index) - set(curated["date"])))
    if available_backfills:
        backfill_rows = secondary.loc[available_backfills].reset_index()
        backfill_rows["source_provider"] = "pykrx_naver"
        backfill_rows["quality_status"] = "provider_backfilled"
        curated = pd.concat([curated, backfill_rows], ignore_index=True).sort_values("date").reset_index(drop=True)

    invalid_ohlc = inconsistent_ohlc_mask(curated)
    if not invalid_ohlc.any():
        return curated

    problem_dates = curated.loc[invalid_ohlc, "date"].tolist()
    missing_replacements = sorted(set(problem_dates) - set(secondary.index))
    if missing_replacements:
        values = ", ".join(day.isoformat() for day in missing_replacements)
        raise ValueError(f"Secondary provider is missing replacement dates: {values}")

    for row_index in curated.index[invalid_ohlc]:
        observation_date = curated.at[row_index, "date"]
        replacement = secondary.loc[observation_date]
        curated.loc[row_index, REPLACEMENT_COLUMNS] = replacement[REPLACEMENT_COLUMNS].values
        curated.at[row_index, "source_provider"] = "pykrx_naver"
        curated.at[row_index, "quality_status"] = "provider_replaced"

    if inconsistent_ohlc_mask(curated).any():
        raise ValueError("Curated data still contains inconsistent OHLC rows.")
    return curated
