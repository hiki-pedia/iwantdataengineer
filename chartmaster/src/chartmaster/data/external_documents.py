"""External news, report, and macro document collection contracts."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ExternalDocument:
    source: str
    url: str
    title: str
    published_at: datetime | None
    related_symbols: tuple[str, ...]
    raw_text: str
    collected_at: datetime


class ExternalDocumentCollector:
    """Placeholder collector for news, reports, and macro documents."""

    def collect(self, symbols: list[str]) -> list[ExternalDocument]:
        raise NotImplementedError("Add news/report collection after market data ETL is stable.")

