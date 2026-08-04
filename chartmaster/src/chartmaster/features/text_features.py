"""Text-derived feature contracts."""

import pandas as pd


def build_daily_sentiment_features(sentiment_rows: pd.DataFrame) -> pd.DataFrame:
    """Aggregate document-level sentiment into daily symbol features."""
    raise NotImplementedError("Implement after the sentiment classifier is selected.")

