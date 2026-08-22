export type Market = "KR" | "US";
export type ModelingTier = "core" | "experimental";
export type DataStatus = "ready" | "watch" | "unavailable";
export type PredictionStatus = "model_not_ready" | "ready" | "stale" | "failed";

export type Asset = {
  symbol: string;
  name: string;
  market: Market;
  exchange: string;
  assetType: string;
  group: string;
  tier: ModelingTier;
  latestClose: number | null;
  return1d: number | null;
  volume: number | null;
  rowCount: number;
  startDate: string;
  endDate: string;
  dataStatus: DataStatus;
  warningCount: number;
};

export type StockCandle = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ma5: number;
  ma20: number;
};

export type DataCheck = {
  name: string;
  scope: string;
  status: "pass" | "watch" | "queued";
  detail: string;
};

export type QualityIssue = {
  symbol: string;
  market: Market;
  severity: "error" | "warning";
  code: string;
  message: string;
  count: number;
  checkedAt: string;
};

export type PipelineRun = {
  name: string;
  status: "success" | "running" | "failed" | "queued" | "planned" | "unavailable";
  lastRun: string | null;
  nextRun: string | null;
  rows: number;
};

export type MarketEvent = {
  id: string;
  symbol: string;
  type: string;
  date: string;
  move: number;
  causeStatus: "not_analyzed" | "ready";
  causeSummary: string | null;
  sourceCount: number;
};

export type Prediction = {
  symbol: string;
  asOf: string | null;
  targetDate: string | null;
  horizonTradingDays: number;
  status: PredictionStatus;
  predictedDirection: "up" | "down" | null;
  upProbability: number | null;
  modelVersion: string | null;
  trainedThrough: string | null;
  dataQuality: DataStatus;
  metricSummary: string | null;
  uncertaintyNote: string;
  forecastPoints: ForecastPoint[];
};

export type ForecastPoint = {
  date: string;
  predictedClose: number;
  lowerBound: number | null;
  upperBound: number | null;
};

export type Report = {
  title: string;
  symbol: string;
  date: string | null;
  status: "ready" | "planned";
};

export type DashboardSnapshot = {
  generatedAt: string;
  sourceMode: "mock" | "api";
  sourceLabel: string;
  assets: Asset[];
  dataChecks: DataCheck[];
  qualityIssues: QualityIssue[];
  pipelineRuns: PipelineRun[];
  events: MarketEvent[];
  predictions: Prediction[];
  reports: Report[];
};

export interface DashboardDataProvider {
  readonly mode: "mock" | "api";
  loadSnapshot(): Promise<DashboardSnapshot>;
  loadPrices(symbol: string, range: string): Promise<StockCandle[]>;
}
