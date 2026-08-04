"""AI report generation contracts."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AssetReportInput:
    symbol: str
    prediction: dict
    latest_features: dict
    external_factor_summary: str
    model_metrics: dict


def generate_asset_report(report_input: AssetReportInput) -> str:
    """Generate a non-advisory explanation report for one asset."""
    raise NotImplementedError("Implement with an LLM after RAG summaries exist.")

