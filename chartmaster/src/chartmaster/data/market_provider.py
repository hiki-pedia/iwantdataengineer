"""Market data provider interfaces."""

from dataclasses import dataclass
from datetime import date
from typing import Protocol

import pandas as pd
import yfinance as yf


@dataclass(frozen=True)
class MarketDataRequest:
    symbol: str
    start: date
    end: date


class MarketDataProvider(Protocol):
    """Protocol for pluggable OHLCV data providers."""

    def fetch_ohlcv(self, request: MarketDataRequest) -> pd.DataFrame:
        """Return OHLCV data for the requested symbol and date range."""
        ...


class YFinanceMarketDataProvider:
    """Fetch daily OHLCV data from Yahoo Finance via yfinance."""

    def fetch_ohlcv(self, request: MarketDataRequest) -> pd.DataFrame:
        dataframe = yf.download(
            request.symbol,
            start=request.start.isoformat(),
            end=request.end.isoformat(),
            auto_adjust=False,
            progress=False,
            threads=False,
        )
        if dataframe.empty:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "adjusted_close", "volume"])

        if isinstance(dataframe.columns, pd.MultiIndex):
            dataframe.columns = dataframe.columns.get_level_values(0)

        dataframe = dataframe.reset_index()
        dataframe = dataframe.rename(
            columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adjusted_close",
                "Volume": "volume",
            }
        )

        output_columns = ["date", "open", "high", "low", "close", "adjusted_close", "volume"]
        dataframe = dataframe[output_columns].copy()
        dataframe["date"] = pd.to_datetime(dataframe["date"]).dt.date
        dataframe = dataframe.sort_values("date").reset_index(drop=True)
        return dataframe
