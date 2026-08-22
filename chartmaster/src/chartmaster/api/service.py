"""Read-only application service backed by server2 market data."""

from __future__ import annotations

import json
import math
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import PurePosixPath

import pandas as pd

from chartmaster.api.schemas import (
    AssetResponse,
    DashboardResponse,
    DataCheckResponse,
    HealthResponse,
    MarketEventResponse,
    PipelineRunResponse,
    PredictionResponse,
    PriceCandleResponse,
    QualityIssueResponse,
    ReportResponse,
)
from chartmaster.config import Asset, load_assets
from chartmaster.storage.local import ObjectStorage, get_object_storage, relative_market_features_path


QUALITY_REPORT_PATH = PurePosixPath("reports/data_quality")
VALID_RANGES = {"ALL", "5Y", "1Y", "6M", "1M", "5D"}


class DashboardService:
    def __init__(self, storage: ObjectStorage | None = None, assets: list[Asset] | None = None, cache_seconds: int = 30):
        self.storage = storage or get_object_storage()
        self.assets = assets or load_assets()
        self.cache_seconds = cache_seconds
        self._cache: DashboardResponse | None = None
        self._cache_created_at = 0.0
        self._cache_lock = threading.Lock()

    def health(self) -> HealthResponse:
        return HealthResponse(status="ok", storage=type(self.storage).__name__, assetCount=len(self.assets))

    @staticmethod
    def quality_report_path(market: str) -> PurePosixPath:
        return QUALITY_REPORT_PATH / f"market={market}" / "latest.json"

    def dashboard(self) -> DashboardResponse:
        now = time.monotonic()
        with self._cache_lock:
            if self._cache and now - self._cache_created_at < self.cache_seconds:
                return self._cache

        quality_reports = self._load_quality_reports()
        quality_assets = {
            item["symbol"]: item
            for report in quality_reports.values()
            for item in report.get("assets", [])
        }
        with ThreadPoolExecutor(max_workers=8) as executor:
            asset_rows = list(executor.map(lambda asset: self._asset_snapshot(asset, quality_assets.get(asset.symbol)), self.assets))

        response = DashboardResponse(
            generatedAt=datetime.now(timezone.utc).isoformat(),
            sourceMode="api",
            sourceLabel="Server 2 live data via FastAPI",
            assets=asset_rows,
            dataChecks=self._data_checks(quality_reports),
            qualityIssues=self._quality_issues(quality_reports),
            pipelineRuns=self._pipeline_status(asset_rows),
            events=self._events(asset_rows),
            predictions=[self._prediction(asset) for asset in asset_rows],
            reports=[
                ReportResponse(title="시장 요약 리포트", symbol="ALL", date=None, status="planned"),
                ReportResponse(title="급등·급락 외부 요인", symbol="ALL", date=None, status="planned"),
                ReportResponse(title="모델 평가 리포트", symbol="ALL", date=None, status="planned"),
            ],
        )
        with self._cache_lock:
            self._cache = response
            self._cache_created_at = time.monotonic()
        return response

    def prices(self, symbol: str, range_name: str) -> list[PriceCandleResponse]:
        if range_name not in VALID_RANGES:
            raise ValueError(f"Unsupported range: {range_name}")
        if symbol not in {asset.symbol for asset in self.assets}:
            raise KeyError(symbol)

        dataframe = self.storage.read_dataframe_csv(relative_market_features_path(symbol))
        required = {"date", "open", "high", "low", "close", "volume"}
        missing = required - set(dataframe.columns)
        if missing:
            raise ValueError(f"Missing price columns: {', '.join(sorted(missing))}")

        dataframe = dataframe.copy()
        dataframe["date"] = pd.to_datetime(dataframe["date"], errors="coerce")
        dataframe = dataframe.dropna(subset=["date", "open", "high", "low", "close", "volume"]).sort_values("date")
        dataframe = self._filter_range(dataframe, range_name)
        if dataframe.empty:
            return []

        ma5 = dataframe["moving_average_5"] if "moving_average_5" in dataframe else dataframe["close"].rolling(5, min_periods=1).mean()
        ma20 = dataframe["moving_average_20"] if "moving_average_20" in dataframe else dataframe["close"].rolling(20, min_periods=1).mean()
        ma5 = ma5.fillna(dataframe["close"].rolling(5, min_periods=1).mean())
        ma20 = ma20.fillna(dataframe["close"].rolling(20, min_periods=1).mean())

        return [
            PriceCandleResponse(
                date=row.date.strftime("%Y-%m-%d"),
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=float(row.volume),
                ma5=float(ma5.loc[index]),
                ma20=float(ma20.loc[index]),
            )
            for index, row in dataframe.iterrows()
        ]

    def _load_quality_reports(self) -> dict[str, dict]:
        reports: dict[str, dict] = {}
        for market in ("KR", "US"):
            path = self.quality_report_path(market)
            try:
                reports[market] = json.loads(self.storage.read_text(path))
            except (FileNotFoundError, json.JSONDecodeError, OSError, subprocess.CalledProcessError):
                reports[market] = {}
        return reports

    def _asset_snapshot(self, asset: Asset, quality: dict | None) -> AssetResponse:
        try:
            tail = self.storage.read_dataframe_csv_tail(relative_market_features_path(asset.symbol), 2)
            last = tail.iloc[-1]
            previous = tail.iloc[-2] if len(tail) > 1 else last
            return_1d = self._finite_float(last.get("return_1d"))
            if return_1d is None and float(previous["close"]) != 0:
                return_1d = float(last["close"]) / float(previous["close"]) - 1
            issues = (quality or {}).get("issues", [])
            errors = sum(1 for issue in issues if issue.get("severity") == "error")
            warnings = sum(1 for issue in issues if issue.get("severity") == "warning")
            return AssetResponse(
                symbol=asset.symbol,
                name=asset.display_name,
                market=asset.market,
                exchange=asset.exchange,
                assetType=asset.asset_type,
                group=asset.group,
                tier=asset.modeling_tier,
                latestClose=float(last["close"]),
                return1d=return_1d,
                volume=float(last["volume"]),
                rowCount=int((quality or {}).get("feature_row_count", 0)),
                startDate=str((quality or {}).get("start_date", "")),
                endDate=str((quality or {}).get("end_date", last["date"])),
                dataStatus="unavailable" if errors else "watch" if warnings or quality is None else "ready",
                warningCount=warnings,
            )
        except (
            FileNotFoundError,
            OSError,
            subprocess.CalledProcessError,
            KeyError,
            IndexError,
            TypeError,
            ValueError,
            pd.errors.EmptyDataError,
            pd.errors.ParserError,
        ):
            return AssetResponse(
                symbol=asset.symbol,
                name=asset.display_name,
                market=asset.market,
                exchange=asset.exchange,
                assetType=asset.asset_type,
                group=asset.group,
                tier=asset.modeling_tier,
                latestClose=None,
                return1d=None,
                volume=None,
                rowCount=int((quality or {}).get("feature_row_count", 0)),
                startDate=str((quality or {}).get("start_date", "")),
                endDate=str((quality or {}).get("end_date", "")),
                dataStatus="unavailable",
                warningCount=len((quality or {}).get("issues", [])),
            )

    @staticmethod
    def _data_checks(reports: dict[str, dict]) -> list[DataCheckResponse]:
        checks = []
        for market, asset_count in (("KR", 12), ("US", 17)):
            summary = reports.get(market, {}).get("summary", {})
            errors = int(summary.get("error_count", 0))
            warnings = int(summary.get("warning_count", 0))
            status = "watch" if errors or warnings or not summary else "pass"
            detail = "리포트 없음" if not summary else f"오류 {errors} / 경고 {warnings}"
            checks.append(DataCheckResponse(name=f"{market} 시장 품질 검사", scope=f"{asset_count} assets", status=status, detail=detail))
        checks.append(DataCheckResponse(name="예측 모델", scope="5 trading days", status="queued", detail="모델 학습 전"))
        return checks

    @staticmethod
    def _quality_issues(reports: dict[str, dict]) -> list[QualityIssueResponse]:
        issues = [
            QualityIssueResponse(
                symbol=str(asset.get("symbol", "")),
                market=market,
                severity=issue.get("severity", "error"),
                code=str(issue.get("code", "unknown_quality_issue")),
                message=str(issue.get("message", "No issue description was recorded.")),
                count=int(issue.get("count", 1)),
                checkedAt=str(report.get("as_of", "")),
            )
            for market, report in reports.items()
            for asset in report.get("assets", [])
            for issue in asset.get("issues", [])
        ]
        return sorted(issues, key=lambda issue: (issue.severity != "error", issue.market, issue.symbol, issue.code))

    @staticmethod
    def _pipeline_status(_assets: list[AssetResponse]) -> list[PipelineRunResponse]:
        result = []
        for name in ("daily_kr_market_data_etl", "daily_us_market_data_etl"):
            result.append(PipelineRunResponse(name=name, status="unavailable", lastRun=None, nextRun=None, rows=0))
        result.append(PipelineRunResponse(name="weekly_model_training", status="planned", lastRun=None, nextRun="Phase 7", rows=0))
        return result

    @staticmethod
    def _events(assets: list[AssetResponse]) -> list[MarketEventResponse]:
        candidates = [asset for asset in assets if asset.return1d is not None and abs(asset.return1d) >= 0.035]
        candidates.sort(key=lambda asset: abs(asset.return1d or 0), reverse=True)
        return [
            MarketEventResponse(
                id=f"evt-{asset.symbol}-{asset.endDate}",
                symbol=asset.symbol,
                type="급등 후보" if (asset.return1d or 0) > 0 else "급락 후보",
                date=asset.endDate,
                move=asset.return1d or 0,
                causeStatus="not_analyzed",
                causeSummary=None,
                sourceCount=0,
            )
            for asset in candidates[:10]
        ]

    @staticmethod
    def _prediction(asset: AssetResponse) -> PredictionResponse:
        return PredictionResponse(
            symbol=asset.symbol,
            asOf=asset.endDate or None,
            targetDate=None,
            horizonTradingDays=5,
            status="model_not_ready",
            predictedDirection=None,
            upProbability=None,
            modelVersion=None,
            trainedThrough=None,
            dataQuality=asset.dataStatus,
            metricSummary=None,
            uncertaintyNote="학습과 시간순 검증이 끝난 모델이 없어 확률을 제공하지 않습니다.",
            forecastPoints=[],
        )

    @staticmethod
    def _filter_range(dataframe: pd.DataFrame, range_name: str) -> pd.DataFrame:
        if range_name == "ALL":
            return dataframe
        if range_name == "5D":
            return dataframe.tail(5)
        end = dataframe["date"].max()
        offsets = {
            "5Y": pd.DateOffset(years=5),
            "1Y": pd.DateOffset(years=1),
            "6M": pd.DateOffset(months=6),
            "1M": pd.DateOffset(months=1),
        }
        return dataframe[dataframe["date"] >= end - offsets[range_name]]

    @staticmethod
    def _finite_float(value: object) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None
