"""Sentiment and event classification contracts."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SentimentResult:
    sentiment_label: str
    sentiment_score: float
    event_type: str | None


class SentimentAnalyzer:
    """Placeholder for LLM or local classifier based sentiment analysis."""

    def analyze(self, text: str) -> SentimentResult:
        raise NotImplementedError("Select LLM or local NLP model before implementing sentiment analysis.")

