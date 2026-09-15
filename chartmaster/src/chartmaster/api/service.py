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
PREDICTION_REPORT_PATH = PurePosixPath("reports/predictions/direction_5d")
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

    @staticmethod
    def prediction_report_path() -> PurePosixPath:
        return PREDICTION_REPORT_PATH / "latest.json"

    @staticmethod
    def prediction_csv_path() -> PurePosixPath:
        return PREDICTION_REPORT_PATH / "latest.csv"

    def dashboard(self) -> DashboardResponse:
        now = time.monotonic()
        with self._cache_lock:
            if self._cache and now - self._cache_created_at < self.cache_seconds:
                return self._cache

        quality_reports = self._load_quality_reports()
        prediction_summary, prediction_rows = self._load_predictions()
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
            dataChecks=self._data_checks(quality_reports, prediction_summary, prediction_rows),
            qualityIssues=self._quality_issues(quality_reports),
            pipelineRuns=self._pipeline_status(asset_rows),
            events=self._events(asset_rows),
            predictions=[self._prediction(asset, prediction_rows.get(asset.symbol), prediction_summary) for asset in asset_rows],
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

    def predictions(self) -> list[PredictionResponse]:
        return self.dashboard().predictions

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

    def _load_predictions(self) -> tuple[dict, dict[str, dict]]:
        try:
            summary = json.loads(self.storage.read_text(self.prediction_report_path()))
        except (FileNotFoundError, json.JSONDecodeError, OSError, subprocess.CalledProcessError):
            summary = {}
        try:
            dataframe = self.storage.read_dataframe_csv(self.prediction_csv_path())
        except (
            FileNotFoundError,
            OSError,
            subprocess.CalledProcessError,
            pd.errors.EmptyDataError,
            pd.errors.ParserError,
        ):
            return summary, {}
        required = {"symbol", "as_of_date", "positive_probability_5d", "predicted_positive_5d"}
        if not required.issubset(dataframe.columns):
            return summary, {}
        return summary, {str(row["symbol"]): row.to_dict() for _, row in dataframe.iterrows()}

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
    def _data_checks(reports: dict[str, dict], prediction_summary: dict, prediction_rows: dict[str, dict]) -> list[DataCheckResponse]:
        checks = []
        for market, asset_count in (("KR", 12), ("US", 17)):
            summary = reports.get(market, {}).get("summary", {})
            errors = int(summary.get("error_count", 0))
            warnings = int(summary.get("warning_count", 0))
            status = "watch" if errors or warnings or not summary else "pass"
            detail = "리포트 없음" if not summary else f"오류 {errors} / 경고 {warnings}"
            checks.append(DataCheckResponse(name=f"{market} 시장 품질 검사", scope=f"{asset_count} assets", status=status, detail=detail))
        if prediction_rows:
            generated_at = str(prediction_summary.get("generated_at", ""))
            checks.append(
                DataCheckResponse(
                    name="예측 모델",
                    scope=f"{len(prediction_rows)} assets / 5 trading days",
                    status="pass",
                    detail=f"latest.csv 연결됨 {generated_at}".strip(),
                )
            )
        else:
            checks.append(DataCheckResponse(name="예측 모델", scope="5 trading days", status="queued", detail="예측 결과 없음"))
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

    def _prediction(self, asset: AssetResponse, prediction_row: dict | None, prediction_summary: dict) -> PredictionResponse:
        if not prediction_row:
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
                uncertaintyNote="학습과 시간순 검증이 끝난 모델 예측 결과가 아직 저장되지 않았습니다.",
                forecastPoints=[],
            )

        probability = self._finite_float(prediction_row.get("positive_probability_5d"))
        threshold = self._finite_float(prediction_row.get("decision_threshold")) or float(prediction_summary.get("decision_threshold", 0.5))
        as_of = str(prediction_row.get("as_of_date") or asset.endDate or "")
        predicted_positive = self._bool_value(prediction_row.get("predicted_positive_5d"))
        if probability is not None:
            predicted_positive = probability >= threshold
        status = "ready" if as_of == asset.endDate else "stale"
        forecast_points = self._forecast_points(asset, as_of, predicted_positive)
        validation_metrics = prediction_summary.get("validation_metrics", {})
        metric_summary = None
        if validation_metrics:
            metric_summary = (
                f"validation F1 {float(validation_metrics.get('f1', 0.0)):.4f}, "
                f"ROC-AUC {float(validation_metrics.get('roc_auc', 0.0)):.4f}"
            )
        return PredictionResponse(
            symbol=asset.symbol,
            asOf=as_of or None,
            targetDate=str(forecast_points[-1]["date"]) if forecast_points else None,
            horizonTradingDays=5,
            status=status,
            predictedDirection="up" if predicted_positive else "down",
            upProbability=probability,
            modelVersion=str(prediction_summary.get("version") or prediction_row.get("model_name") or ""),
            trainedThrough=as_of or None,
            dataQuality=asset.dataStatus,
            metricSummary=metric_summary,
            uncertaintyNote="현재 예측선은 방향 확률을 차트에 표시하기 위한 5거래일 시각화이며, 가격 회귀 모델의 목표가가 아닙니다.",
            forecastPoints=forecast_points,
        )

    def _forecast_points(self, asset: AssetResponse, as_of: str, predicted_positive: bool) -> list[dict[str, float | str]]:
        if asset.latestClose is None or not as_of:
            return []
        try:
            tail = self.storage.read_dataframe_csv_tail(relative_market_features_path(asset.symbol), 30)
            volatility = self._finite_float(tail.iloc[-1].get("volatility_20"))
            if volatility is None:
                close = pd.to_numeric(tail["close"], errors="coerce")
                volatility = float(close.pct_change(fill_method=None).dropna().std())
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
            volatility = 0.02
        volatility = 0.02 if volatility is None or not math.isfinite(volatility) else volatility
        total_move = min(max(abs(volatility) * math.sqrt(5), 0.01), 0.08)
        if not predicted_positive:
            total_move *= -1
        dates = pd.bdate_range(pd.to_datetime(as_of) + pd.offsets.BDay(1), periods=5)
        return [
            {
                "date": day.strftime("%Y-%m-%d"),
                "predictedClose": float(asset.latestClose * (1 + total_move * ((index + 1) / 5))),
                "lowerBound": float(asset.latestClose * (1 + (total_move - abs(total_move) * 0.5) * ((index + 1) / 5))),
                "upperBound": float(asset.latestClose * (1 + (total_move + abs(total_move) * 0.5) * ((index + 1) / 5))),
            }
            for index, day in enumerate(dates)
        ]

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

    @staticmethod
    def _bool_value(value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes", "y"}
        return bool(value)
