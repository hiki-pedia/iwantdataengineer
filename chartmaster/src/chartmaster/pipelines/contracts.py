"""Shared pipeline data contracts."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PipelineRunRecord:
    pipeline_name: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    message: str | None = None

