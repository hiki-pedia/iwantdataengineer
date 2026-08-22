import assetRegistry from "../../../config/assets.json";
import type { Asset, DashboardSnapshot, Prediction, QualityIssue, StockCandle } from "./contracts";

type AssetSnapshot = [number, string, string, number, number, number];

const snapshots: Record<string, AssetSnapshot> = {
  "000660.KS": [6663, "2000-01-04", "2026-08-21", 1730000, 4274294, 0.023063],
  "005930.KS": [6663, "2000-01-04", "2026-08-21", 281500, 27746471, 0.038745],
  "022100.KS": [6427, "2000-11-29", "2026-08-21", 19510, 163411, -0.045966],
  "005380.KS": [6663, "2000-01-04", "2026-08-21", 415000, 373056, -0.005988],
  "005490.KS": [6663, "2000-01-04", "2026-08-21", 310000, 235539, -0.03577],
  "000810.KS": [6663, "2000-01-04", "2026-08-21", 661000, 116996, 0.062701],
  "066570.KS": [6062, "2002-04-24", "2026-08-21", 194500, 858709, -0.039506],
  "034730.KS": [4131, "2009-11-11", "2026-08-21", 586000, 189218, 0.03169],
  "030200.KS": [6663, "2000-01-04", "2026-08-21", 52400, 206894, 0.005758],
  "015760.KS": [6663, "2000-01-04", "2026-08-21", 31750, 833434, -0.001572],
  "055550.KS": [6663, "2000-01-04", "2026-08-21", 104100, 1345887, 0.029674],
  "105560.KS": [6148, "2001-12-25", "2026-08-21", 164300, 1165965, 0.026875],
  MU: [10638, "1984-06-01", "2026-08-21", 966.78, 20990385, -0.007749],
  WDC: [12050, "1978-10-31", "2026-08-21", 459.44, 4205970, -0.020488],
  SPY: [8448, "1993-01-29", "2026-08-21", 765.72, 38583716, 0.004091],
  QQQ: [6906, "1999-03-10", "2026-08-21", 713.44, 33084596, 0.003531],
  AAPL: [11515, "1980-12-12", "2026-08-21", 309.35, 42216056, -0.006264],
  MSFT: [10189, "1986-03-13", "2026-08-21", 483.24, 21856586, 0.004344],
  IBM: [16268, "1962-01-02", "2026-08-21", 235.68, 2984735, 0.008516],
  KO: [16268, "1962-01-02", "2026-08-21", 91.1, 15527401, 0.00663],
  JPM: [11703, "1980-03-17", "2026-08-21", 351.58, 5579895, 0.000085],
  XOM: [16268, "1962-01-02", "2026-08-21", 165.11, 14225679, -0.006259],
  CAT: [16268, "1962-01-02", "2026-08-21", 827.9, 2030466, 0.015342],
  PG: [16268, "1962-01-02", "2026-08-21", 144.68, 8049649, 0.01196],
  SNDK: [382, "2025-02-13", "2026-08-21", 1596.08, 7503783, -0.002836],
  SOXL: [4138, "2010-03-11", "2026-08-21", 120.6, 47525925, -0.013174],
  NASA: [100, "2026-03-31", "2026-08-21", 24.64, 870616, 0.013158],
  SPCX: [49, "2026-06-12", "2026-08-21", 136.97, 77453430, 0.022164],
  RAM: [42, "2026-06-24", "2026-08-21", 13.15, 11492446, 0.005352]
};

const krWarnings: Record<string, number> = {
  "000660.KS": 2,
  "005930.KS": 1,
  "022100.KS": 1,
  "005380.KS": 1,
  "005490.KS": 1,
  "000810.KS": 1,
  "066570.KS": 1,
  "030200.KS": 1,
  "015760.KS": 1,
  "055550.KS": 1,
  "105560.KS": 1
};

export const mockAssets: Asset[] = assetRegistry.map((row) => {
  const [rowCount, startDate, endDate, latestClose, volume, return1d] = snapshots[row.symbol];
  const warningCount = krWarnings[row.symbol] ?? 0;
  return {
    symbol: row.symbol,
    name: row.display_name,
    market: row.market as Asset["market"],
    exchange: row.exchange,
    assetType: row.asset_type,
    group: row.group,
    tier: row.modeling_tier as Asset["tier"],
    latestClose,
    return1d,
    volume,
    rowCount,
    startDate,
    endDate,
    dataStatus: warningCount > 0 ? "watch" : "ready",
    warningCount
  };
});

const predictions: Prediction[] = mockAssets.map((asset) => ({
  symbol: asset.symbol,
  asOf: asset.endDate,
  targetDate: null,
  horizonTradingDays: 5,
  status: "model_not_ready",
  predictedDirection: null,
  upProbability: null,
  modelVersion: null,
  trainedThrough: null,
  dataQuality: asset.dataStatus,
  metricSummary: null,
  uncertaintyNote: "학습과 시간순 검증이 끝난 모델이 없어 확률을 제공하지 않습니다.",
  forecastPoints: []
}));

const qualityIssues: QualityIssue[] = Object.keys(krWarnings).map((symbol) => ({
  symbol,
  market: "KR",
  severity: "warning",
  code: "missing_expected_sessions",
  message: "Missing expected exchange sessions: 2007-03-02",
  count: 1,
  checkedAt: "2026-08-22"
}));

qualityIssues.push({
  symbol: "000660.KS",
  market: "KR",
  severity: "warning",
  code: "non_positive_adjusted_close",
  message: "Adjusted close contains zero or negative values; retain raw data and verify with another provider.",
  count: 778,
  checkedAt: "2026-08-22"
});

export const mockSnapshot: DashboardSnapshot = {
  generatedAt: "2026-08-22T16:40:47+09:00",
  sourceMode: "mock",
  sourceLabel: "Server 2 품질검사 스냅샷 / 차트 데모",
  assets: mockAssets,
  dataChecks: [
    { name: "한국장 품질 검사", scope: "12 assets", status: "watch", detail: "오류 0 / 미해결 경고 12" },
    { name: "미국장 품질 검사", scope: "17 assets", status: "pass", detail: "오류 0 / 경고 0" },
    { name: "중복 날짜", scope: "raw and curated", status: "pass", detail: "중복 row 0개" },
    { name: "한국장 보조 공급자", scope: "pykrx_naver", status: "watch", detail: "KRX 인증 원천 검증 대기" }
  ],
  qualityIssues,
  pipelineRuns: [
    { name: "daily_kr_market_data_etl", status: "success", lastRun: "2026-08-22 16:25", nextRun: "스케줄 실행", rows: 12 },
    { name: "daily_us_market_data_etl", status: "success", lastRun: "2026-08-22 검증", nextRun: "스케줄 실행", rows: 17 },
    { name: "weekly_model_training", status: "planned", lastRun: null, nextRun: "Phase 7", rows: 0 }
  ],
  events: [
    { id: "evt-000810-20260821", symbol: "000810.KS", type: "급등 후보", date: "2026-08-21", move: 0.062701, causeStatus: "not_analyzed", causeSummary: null, sourceCount: 0 },
    { id: "evt-022100-20260821", symbol: "022100.KS", type: "급락 후보", date: "2026-08-21", move: -0.045966, causeStatus: "not_analyzed", causeSummary: null, sourceCount: 0 },
    { id: "evt-066570-20260821", symbol: "066570.KS", type: "급락 후보", date: "2026-08-21", move: -0.039506, causeStatus: "not_analyzed", causeSummary: null, sourceCount: 0 }
  ],
  predictions,
  reports: [
    { title: "시장 요약 리포트", symbol: "ALL", date: null, status: "planned" },
    { title: "급등·급락 외부 요인", symbol: "ALL", date: null, status: "planned" },
    { title: "모델 평가 리포트", symbol: "ALL", date: null, status: "planned" }
  ]
};

const tradingDates = (count: number) => {
  const dates: string[] = [];
  const cursor = new Date("2026-08-21T00:00:00Z");
  while (dates.length < count) {
    const day = cursor.getUTCDay();
    if (day !== 0 && day !== 6) dates.unshift(cursor.toISOString().slice(0, 10));
    cursor.setUTCDate(cursor.getUTCDate() - 1);
  }
  return dates;
};

const seedFor = (symbol: string) => [...symbol].reduce((sum, char) => sum + char.charCodeAt(0), 0);

const movingAverage = (values: number[], index: number, window: number) => {
  const start = Math.max(0, index - window + 1);
  const slice = values.slice(start, index + 1);
  return slice.reduce((sum, value) => sum + value, 0) / slice.length;
};

export function buildMockCandles(asset: Asset, count = 126): StockCandle[] {
  const seed = seedFor(asset.symbol);
  const closes: number[] = [];
  const priceScale = asset.latestClose ?? 100;
  return tradingDates(count).map((date, index) => {
    const progress = index / Math.max(1, count - 1);
    const trend = priceScale * (0.84 + progress * 0.18);
    const cycle = Math.sin(index / 4.4 + seed) * priceScale * 0.035 + Math.cos(index / 10 + seed) * priceScale * 0.024;
    const close = Math.max(priceScale * 0.35, trend + cycle);
    const previous = closes[index - 1] ?? close * (0.992 + Math.sin(seed) * 0.008);
    const open = previous + Math.sin(index / 2.7 + seed) * priceScale * 0.012;
    const high = Math.max(open, close) + priceScale * (0.01 + Math.abs(Math.sin(index / 3.1 + seed)) * 0.025);
    const low = Math.min(open, close) - priceScale * (0.01 + Math.abs(Math.cos(index / 2.8 + seed)) * 0.022);
    const volume = Math.round((asset.volume ?? 1000000) * (0.45 + Math.abs(Math.sin(index / 5 + seed)) * 0.9));
    closes.push(close);
    return { date, open, high, low, close, volume, ma5: movingAverage(closes, index, 5), ma20: movingAverage(closes, index, 20) };
  });
}
