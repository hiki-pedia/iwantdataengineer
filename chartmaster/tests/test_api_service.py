import json

import pandas as pd
import pytest

from chartmaster.api.service import DashboardService
from chartmaster.config import Asset
from chartmaster.storage.local import LocalObjectStorage, relative_market_features_path


TEST_ASSET = Asset(
    symbol="TEST",
    display_name="Test Asset",
    market="KR",
    exchange="KRX",
    asset_type="stock",
    group="test",
    modeling_tier="core",
    notes="",
)


def make_service(tmp_path) -> DashboardService:
    storage = LocalObjectStorage(tmp_path)
    dates = pd.bdate_range("2025-01-01", periods=300)
    close = pd.Series(range(100, 400), dtype="float64")
    features = pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "open": close - 1,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "volume": 1000 + close,
            "return_1d": close.pct_change(),
            "moving_average_5": close.rolling(5).mean(),
            "moving_average_20": close.rolling(20).mean(),
        }
    )
    storage.write_dataframe_csv(features, relative_market_features_path(TEST_ASSET.symbol))
    quality_report = {
        "as_of": "2026-08-22",
        "summary": {"error_count": 0, "warning_count": 1},
        "assets": [
            {
                "symbol": "TEST",
                "feature_row_count": 300,
                "start_date": dates.min().strftime("%Y-%m-%d"),
                "end_date": dates.max().strftime("%Y-%m-%d"),
                "issues": [{"severity": "warning", "code": "test_warning", "message": "Test warning.", "count": 2}],
            }
        ],
    }
    storage.write_text(
        json.dumps(quality_report),
        DashboardService.quality_report_path("KR"),
    )
    return DashboardService(storage=storage, assets=[TEST_ASSET], cache_seconds=0)


def test_dashboard_uses_real_storage_values_and_does_not_invent_predictions(tmp_path) -> None:
    dashboard = make_service(tmp_path).dashboard()

    assert dashboard.sourceMode == "api"
    assert dashboard.assets[0].latestClose == 399
    assert dashboard.assets[0].rowCount == 300
    assert dashboard.assets[0].dataStatus == "watch"
    assert dashboard.qualityIssues[0].symbol == "TEST"
    assert dashboard.qualityIssues[0].count == 2
    assert dashboard.qualityIssues[0].checkedAt == "2026-08-22"
    assert dashboard.predictions[0].status == "model_not_ready"
    assert dashboard.predictions[0].forecastPoints == []
    assert dashboard.pipelineRuns[0].status == "unavailable"
    assert dashboard.pipelineRuns[0].lastRun is None
    assert dashboard.pipelineRuns[0].rows == 0


def test_prices_filters_range_and_preserves_moving_averages(tmp_path) -> None:
    service = make_service(tmp_path)
    prices = service.prices("TEST", "5D")
    all_prices = service.prices("TEST", "ALL")

    assert len(prices) == 5
    assert len(all_prices) == 300
    assert prices[0].date < prices[-1].date
    assert prices[-1].close == 399
    assert prices[-1].ma5 == 397


def test_prices_rejects_unknown_symbol_and_range(tmp_path) -> None:
    service = make_service(tmp_path)

    with pytest.raises(KeyError):
        service.prices("UNKNOWN", "5D")
    with pytest.raises(ValueError):
        service.prices("TEST", "MAX")
