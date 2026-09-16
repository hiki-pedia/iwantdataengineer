"""Market data provider interfaces."""

from dataclasses import dataclass
from datetime import date, timedelta
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


class PykrxNaverMarketDataProvider:
    """Fetch adjusted Korean OHLCV through pykrx's public Naver-backed path."""

    def fetch_ohlcv(self, request: MarketDataRequest) -> pd.DataFrame:
        from pykrx import stock

        ticker = request.symbol.split(".", 1)[0]
        inclusive_end = request.end - timedelta(days=1)
        dataframe = stock.get_market_ohlcv(
            request.start.strftime("%Y%m%d"),
            inclusive_end.strftime("%Y%m%d"),
            ticker,
            adjusted=True,
        )
        if dataframe.empty:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "adjusted_close", "volume"])

        dataframe = dataframe.reset_index().rename(
            columns={
                "날짜": "date",
                "시가": "open",
                "고가": "high",
                "저가": "low",
                "종가": "close",
                "거래량": "volume",
            }
        )
        dataframe["adjusted_close"] = dataframe["close"]
        output_columns = ["date", "open", "high", "low", "close", "adjusted_close", "volume"]
        output = dataframe[output_columns].copy()
        output["date"] = pd.to_datetime(output["date"]).dt.date
        return output.sort_values("date").reset_index(drop=True)
