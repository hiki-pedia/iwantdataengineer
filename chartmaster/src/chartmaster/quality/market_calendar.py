"""Exchange-session helpers used by market data quality checks."""

from __future__ import annotations

from datetime import date
from functools import lru_cache

import exchange_calendars as xcals
import pandas as pd


CALENDAR_BY_MARKET = {
    "KR": "XKRX",
    "US": "XNYS",
}

CALENDAR_START_BY_MARKET = {
    "KR": "1999-01-01",
    "US": "1970-01-01",
}

SESSION_VALIDATION_START_BY_MARKET = {
    "KR": date(2000, 1, 1),
    "US": date(1970, 1, 1),
}

# XKRX 4.13.2 misses a few one-off Korean market closures we verified separately.
KNOWN_NON_SESSIONS = {
    "KR": {
        date(2007, 3, 2),
        date(2026, 6, 3),
        date(2026, 7, 17),
    },
    "US": set(),
}


@lru_cache(maxsize=2)
def _market_calendar(market: str):
    calendar_name = CALENDAR_BY_MARKET.get(market)
    if not calendar_name:
        raise ValueError(f"No exchange calendar configured for market {market}")
    return xcals.get_calendar(
        calendar_name,
        start=CALENDAR_START_BY_MARKET[market],
        end="2028-12-31",
    )


def expected_market_sessions(market: str, start: date, end: date) -> set[date]:
    """Return expected exchange sessions for an inclusive date range."""
    calendar = _market_calendar(market)
    effective_start = max(start, SESSION_VALIDATION_START_BY_MARKET[market])
    start_timestamp = pd.Timestamp(effective_start)
    end_timestamp = pd.Timestamp(end)
    sessions = calendar.sessions[(calendar.sessions >= start_timestamp) & (calendar.sessions <= end_timestamp)]
    return {timestamp.date() for timestamp in sessions} - KNOWN_NON_SESSIONS[market]
