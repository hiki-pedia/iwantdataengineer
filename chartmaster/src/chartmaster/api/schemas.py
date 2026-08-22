"""HTTP response contracts shared with the Electron client."""

from typing import Literal

from pydantic import BaseModel


DataStatus = Literal["ready", "watch", "unavailable"]


class AssetResponse(BaseModel):
    symbol: str
    name: str
    market: Literal["KR", "US"]
    exchange: str
    assetType: str
    group: str
    tier: Literal["core", "experimental"]
    latestClose: float | None
    return1d: float | None
    volume: float | None
    rowCount: int
    startDate: str
    endDate: str
    dataStatus: DataStatus
    warningCount: int


class PriceCandleResponse(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    ma5: float
    ma20: float


class DataCheckResponse(BaseModel):
    name: str
    scope: str
    status: Literal["pass", "watch", "queued"]
    detail: str


class PipelineRunResponse(BaseModel):
    name: str
    status: Literal["success", "running", "failed", "queued", "planned", "unavailable"]
    lastRun: str | None
    nextRun: str | None
    rows: int


class MarketEventResponse(BaseModel):
    id: str
    symbol: str
    type: str
    date: str
    move: float
    causeStatus: Literal["not_analyzed", "ready"]
    causeSummary: str | None
    sourceCount: int


class ForecastPointResponse(BaseModel):
    date: str
    predictedClose: float
    lowerBound: float | None
    upperBound: float | None


class PredictionResponse(BaseModel):
    symbol: str
    asOf: str | None
    targetDate: str | None
    horizonTradingDays: int
    status: Literal["model_not_ready", "ready", "stale", "failed"]
    predictedDirection: Literal["up", "down"] | None
    upProbability: float | None
    modelVersion: str | None
    trainedThrough: str | None
    dataQuality: DataStatus
    metricSummary: str | None
    uncertaintyNote: str
    forecastPoints: list[ForecastPointResponse]


class ReportResponse(BaseModel):
    title: str
    symbol: str
    date: str | None
    status: Literal["ready", "planned"]


class DashboardResponse(BaseModel):
    generatedAt: str
    sourceMode: Literal["api"]
    sourceLabel: str
    assets: list[AssetResponse]
    dataChecks: list[DataCheckResponse]
    pipelineRuns: list[PipelineRunResponse]
    events: list[MarketEventResponse]
    predictions: list[PredictionResponse]
    reports: list[ReportResponse]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    storage: str
    assetCount: int
