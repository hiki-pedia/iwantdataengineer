import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertTriangle,
  BarChart3,
  Brain,
  CheckCircle2,
  Database,
  Expand,
  FileText,
  LineChart,
  SearchCheck,
  Workflow,
  X
} from "lucide-react";
import "./styles.css";

type AppRoute = `asset:${string}` | "data-status" | "data-check" | "events" | "predictions" | "pipelines" | "reports";

type Asset = {
  symbol: string;
  name: string;
  market: "KR" | "US";
  exchange: string;
  tier: "core" | "experimental";
  latestClose: number;
  return1d: number;
  volume: number;
  rowCount: number;
  startDate: string;
  endDate: string;
  dataStatus: "ready" | "watch" | "planned";
};

type StockCandle = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ma5: number;
  ma20: number;
};

const assets: Asset[] = [
  {
    symbol: "000660.KS",
    name: "SK하이닉스",
    market: "KR",
    exchange: "KRX",
    tier: "core",
    latestClose: 198500,
    return1d: 0.042,
    volume: 3600000,
    rowCount: 6631,
    startDate: "2000-01-04",
    endDate: "2026-08-21",
    dataStatus: "ready"
  },
  {
    symbol: "005930.KS",
    name: "삼성전자",
    market: "KR",
    exchange: "KRX",
    tier: "core",
    latestClose: 75400,
    return1d: 0.018,
    volume: 12400000,
    rowCount: 6628,
    startDate: "2000-01-04",
    endDate: "2026-08-21",
    dataStatus: "ready"
  },
  {
    symbol: "MU",
    name: "마이크론 테크놀로지",
    market: "US",
    exchange: "NASDAQ",
    tier: "core",
    latestClose: 132.4,
    return1d: 0.031,
    volume: 17800000,
    rowCount: 6684,
    startDate: "2000-01-03",
    endDate: "2026-08-21",
    dataStatus: "ready"
  },
  {
    symbol: "AAPL",
    name: "애플",
    market: "US",
    exchange: "NASDAQ",
    tier: "core",
    latestClose: 214.1,
    return1d: -0.012,
    volume: 52200000,
    rowCount: 6690,
    startDate: "2000-01-03",
    endDate: "2026-08-21",
    dataStatus: "ready"
  },
  {
    symbol: "SOXL",
    name: "미국 반도체 3배 레버리지 ETF",
    market: "US",
    exchange: "NYSEARCA",
    tier: "experimental",
    latestClose: 51.2,
    return1d: -0.064,
    volume: 45100000,
    rowCount: 4012,
    startDate: "2010-03-11",
    endDate: "2026-08-21",
    dataStatus: "watch"
  }
];

const dataChecks = [
  { name: "원천 OHLCV 파일", scope: "market_data", status: "pass", detail: "최신 파일 확인" },
  { name: "필수 컬럼", scope: "open high low close volume", status: "pass", detail: "스키마 계약 일치" },
  { name: "중복 날짜", scope: "date index", status: "pass", detail: "중복 row 0개" },
  { name: "피처 결측률", scope: "processed/features", status: "watch", detail: "이동 윈도우 초반 결측은 정상 범위" },
  { name: "미국장 최신 종가", scope: "daily_us_market_data_etl", status: "queued", detail: "다음 장마감 수집 대기" }
] as const;

const pipelineRuns = [
  { name: "daily_kr_market_data_etl", status: "success", lastRun: "2026-08-21 16:12", nextRun: "2026-08-24 16:10", rows: 120 },
  { name: "daily_us_market_data_etl", status: "queued", lastRun: "2026-08-21 17:33", nextRun: "2026-08-24 17:30", rows: 170 },
  { name: "weekly_model_training", status: "planned", lastRun: "-", nextRun: "Phase 7", rows: 0 }
];

const events = [
  { symbol: "000660.KS", type: "급등", date: "2026-08-19", move: 0.064, cause: "메모리 업황 강세" },
  { symbol: "AAPL", type: "급락", date: "2026-08-18", move: -0.047, cause: "기술주 위험 회피" },
  { symbol: "SOXL", type: "변동성 확대", date: "2026-08-20", move: -0.082, cause: "레버리지 ETF 증폭 효과" }
];

const reports = [
  { title: "시장 요약 스냅샷", symbol: "ALL", date: "2026-08-21", status: "ready" },
  { title: "SK하이닉스 외부 요인", symbol: "000660.KS", date: "2026-08-21", status: "ready" },
  { title: "기준선 모델 상태", symbol: "ALL", date: "Phase 6", status: "planned" }
];

const tradingDates = (count: number) => {
  const dates: string[] = [];
  const cursor = new Date("2026-08-21T00:00:00Z");
  while (dates.length < count) {
    const day = cursor.getUTCDay();
    if (day !== 0 && day !== 6) {
      dates.unshift(cursor.toISOString().slice(5, 10));
    }
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

const buildCandles = (asset: Asset, count = 96): StockCandle[] => {
  const seed = seedFor(asset.symbol);
  const closes: number[] = [];
  const dates = tradingDates(count);
  const priceScale = asset.latestClose;
  return dates.map((date, index) => {
    const progress = index / Math.max(1, count - 1);
    const trend = priceScale * (0.84 + progress * 0.18);
    const cycle = Math.sin(index / 4.4 + seed) * priceScale * 0.035 + Math.cos(index / 10 + seed) * priceScale * 0.024;
    const close = Math.max(priceScale * 0.35, trend + cycle);
    const previous = closes[index - 1] ?? close * (0.992 + Math.sin(seed) * 0.008);
    const open = previous + Math.sin(index / 2.7 + seed) * priceScale * 0.012;
    const high = Math.max(open, close) + priceScale * (0.01 + Math.abs(Math.sin(index / 3.1 + seed)) * 0.025);
    const low = Math.min(open, close) - priceScale * (0.01 + Math.abs(Math.cos(index / 2.8 + seed)) * 0.022);
    const volume = Math.round(asset.volume * (0.45 + Math.abs(Math.sin(index / 5 + seed)) * 0.9 + Math.abs(close - open) / priceScale));
    closes.push(close);
    return {
      date,
      open,
      high,
      low,
      close,
      volume,
      ma5: movingAverage(closes, index, 5),
      ma20: movingAverage(closes, index, 20)
    };
  });
};

function App() {
  const [route, setRoute] = useState<AppRoute>(`asset:${assets[0].symbol}`);
  const [isExpanded, setIsExpanded] = useState(false);
  const selectedSymbol = route.startsWith("asset:") ? route.slice("asset:".length) : assets[0].symbol;
  const selectedAsset = assets.find((asset) => asset.symbol === selectedSymbol) ?? assets[0];

  return (
    <div className="shell">
      <Sidebar route={route} setRoute={setRoute} />
      <main>
        {route.startsWith("asset:") && <AssetPage asset={selectedAsset} isExpanded={isExpanded} setIsExpanded={setIsExpanded} />}
        {route === "data-status" && <DataStatusPage />}
        {route === "data-check" && <DataCheckPage />}
        {route === "events" && <EventsPage setRoute={setRoute} />}
        {route === "predictions" && <PredictionsPage setRoute={setRoute} />}
        {route === "pipelines" && <PipelinesPage />}
        {route === "reports" && <ReportsPage />}
      </main>
    </div>
  );
}

function Sidebar({ route, setRoute }: { route: AppRoute; setRoute: (route: AppRoute) => void }) {
  return (
    <aside>
      <div className="brand">
        <BarChart3 />
        <strong>ChartMaster</strong>
      </div>

      <NavSection title="대시보드">
        {assets.map((asset) => (
          <button
            className={route === `asset:${asset.symbol}` ? "active nested" : "nested"}
            key={asset.symbol}
            onClick={() => setRoute(`asset:${asset.symbol}`)}
          >
            <LineChart size={16} />
            <span>
              <strong>{asset.symbol}</strong>
              <small>{asset.name}</small>
            </span>
          </button>
        ))}
      </NavSection>

      <NavSection title="데이터">
        <button className={route === "data-status" ? "active nested" : "nested"} onClick={() => setRoute("data-status")}>
          <Database size={16} />
          <span>
            <strong>데이터 상태</strong>
            <small>저장소와 최신성</small>
          </span>
        </button>
        <button className={route === "data-check" ? "active nested" : "nested"} onClick={() => setRoute("data-check")}>
          <SearchCheck size={16} />
          <span>
            <strong>데이터 검증</strong>
            <small>스키마와 품질</small>
          </span>
        </button>
      </NavSection>

      <NavSection title="분석">
        <NavButton active={route === "events"} icon={<AlertTriangle size={16} />} label="이벤트" onClick={() => setRoute("events")} />
        <NavButton active={route === "predictions"} icon={<Brain size={16} />} label="예측" onClick={() => setRoute("predictions")} />
        <NavButton active={route === "pipelines"} icon={<Workflow size={16} />} label="파이프라인" onClick={() => setRoute("pipelines")} />
        <NavButton active={route === "reports"} icon={<FileText size={16} />} label="리포트" onClick={() => setRoute("reports")} />
      </NavSection>
    </aside>
  );
}

function NavSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="nav-section">
      <div className="nav-title">{title}</div>
      {children}
    </section>
  );
}

function NavButton({ active, icon, label, onClick }: { active: boolean; icon: React.ReactNode; label: string; onClick: () => void }) {
  return (
    <button className={active ? "active" : ""} onClick={onClick}>
      {icon}
      {label}
    </button>
  );
}

function AssetPage({ asset, isExpanded, setIsExpanded }: { asset: Asset; isExpanded: boolean; setIsExpanded: (value: boolean) => void }) {
  const candles = useMemo(() => buildCandles(asset), [asset]);
  const last = candles[candles.length - 1];
  const prev = candles[candles.length - 2] ?? last;
  const change = last.close / prev.close - 1;

  return (
    <section className="asset-page">
      <header className="asset-header">
        <div>
          <h1>{asset.symbol}</h1>
          <span>{asset.name}</span>
        </div>
        <div className="header-pills">
          <span>{asset.market}</span>
          <span>{asset.exchange}</span>
          <span>{tierText(asset.tier)}</span>
          <em className={asset.dataStatus}>{statusText(asset.dataStatus)}</em>
        </div>
      </header>

      <section className="quote-strip">
        <Quote label="종가" value={formatPrice(last.close, asset)} />
        <Quote label="1D" value={formatPercent(change)} tone={change >= 0 ? "up" : "down"} />
        <Quote label="거래량" value={formatCompact(last.volume)} />
        <Quote label="데이터 기간" value={`${asset.startDate} - ${asset.endDate}`} />
      </section>

      <section className="asset-layout">
        <div className="chart-panel">
          <StockChart candles={candles} asset={asset} onExpand={() => setIsExpanded(true)} />
        </div>
        <aside className="inspector">
          <h2>데이터</h2>
          <InfoRow label="행 수" value={asset.rowCount.toLocaleString()} />
          <InfoRow label="최신 일자" value={asset.endDate} />
          <InfoRow label="OHLCV" value="정상" tone="ready" />
          <InfoRow label="피처" value="정상" tone="ready" />
          <InfoRow label="등급" value={tierText(asset.tier)} />
          <h2>신호</h2>
          <InfoRow label="예측 기간" value="5D" />
          <InfoRow label="모델" value="기준선 자리" />
          <InfoRow label="신뢰도" value={asset.tier === "core" ? "중간" : "낮음"} tone={asset.tier === "core" ? "ready" : "watch"} />
        </aside>
      </section>

      {isExpanded && (
        <div className="chart-overlay">
          <div className="chart-modal">
            <StockChart candles={candles} asset={asset} expanded onClose={() => setIsExpanded(false)} />
          </div>
        </div>
      )}
    </section>
  );
}

function DataStatusPage() {
  return (
    <Page title="데이터 상태" icon={<Database />}>
      <section className="status-grid">
        {assets.map((asset) => (
          <article className="status-card" key={asset.symbol}>
            <div>
              <strong>{asset.symbol}</strong>
              <span>{asset.name}</span>
            </div>
            <em className={asset.dataStatus}>{statusText(asset.dataStatus)}</em>
            <InfoRow label="원천 행 수" value={asset.rowCount.toLocaleString()} />
            <InfoRow label="최신 일자" value={asset.endDate} />
            <InfoRow label="거래량" value={formatCompact(asset.volume)} />
          </article>
        ))}
      </section>
    </Page>
  );
}

function DataCheckPage() {
  return (
    <Page title="데이터 검증" icon={<SearchCheck />}>
      <section className="panel-list">
        {dataChecks.map((check) => (
          <article className="check-row" key={check.name}>
            <CheckCircle2 className={check.status} />
            <div>
              <strong>{check.name}</strong>
              <span>{check.scope}</span>
            </div>
            <em className={check.status}>{statusText(check.status)}</em>
            <span>{check.detail}</span>
          </article>
        ))}
      </section>
    </Page>
  );
}

function EventsPage({ setRoute }: { setRoute: (route: AppRoute) => void }) {
  return (
    <Page title="이벤트" icon={<AlertTriangle />}>
      <section className="panel-list">
        {events.map((event) => (
          <button className="event-row" key={`${event.symbol}-${event.date}`} onClick={() => setRoute(`asset:${event.symbol}`)}>
            <strong>{event.symbol}</strong>
            <span>{event.date}</span>
            <span>{event.type}</span>
            <em className={event.move >= 0 ? "up" : "down"}>{formatPercent(event.move)}</em>
            <span>{event.cause}</span>
          </button>
        ))}
      </section>
    </Page>
  );
}

function PredictionsPage({ setRoute }: { setRoute: (route: AppRoute) => void }) {
  return (
    <Page title="예측" icon={<Brain />}>
      <section className="panel-list">
        {assets.map((asset, index) => {
          const probability = 0.52 + Math.sin(seedFor(asset.symbol)) * 0.16;
          return (
            <button className="prediction-row" key={asset.symbol} onClick={() => setRoute(`asset:${asset.symbol}`)}>
              <strong>{asset.symbol}</strong>
              <span>5일 방향성</span>
              <em className={probability >= 0.5 ? "up" : "down"}>{Math.round(probability * 100)}%</em>
              <span>{index < 3 ? "기준선 자리" : "대기"}</span>
            </button>
          );
        })}
      </section>
    </Page>
  );
}

function PipelinesPage() {
  return (
    <Page title="파이프라인" icon={<Workflow />}>
      <section className="status-grid pipeline-grid">
        {pipelineRuns.map((run) => (
          <article className="status-card" key={run.name}>
            <div>
              <strong>{run.name}</strong>
              <span>{run.lastRun}</span>
            </div>
            <em className={run.status}>{statusText(run.status)}</em>
            <InfoRow label="다음 실행" value={run.nextRun} />
            <InfoRow label="행 수" value={run.rows.toLocaleString()} />
          </article>
        ))}
      </section>
    </Page>
  );
}

function ReportsPage() {
  return (
    <Page title="리포트" icon={<FileText />}>
      <section className="panel-list">
        {reports.map((report) => (
          <article className="report-row" key={report.title}>
            <FileText />
            <div>
              <strong>{report.title}</strong>
              <span>{report.symbol} / {report.date}</span>
            </div>
            <em className={report.status}>{statusText(report.status)}</em>
          </article>
        ))}
      </section>
    </Page>
  );
}

function Page({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="page">
      <header className="page-header">
        {icon}
        <h1>{title}</h1>
      </header>
      {children}
    </section>
  );
}

function StockChart({
  candles,
  asset,
  expanded,
  onExpand,
  onClose
}: {
  candles: StockCandle[];
  asset: Asset;
  expanded?: boolean;
  onExpand?: () => void;
  onClose?: () => void;
}) {
  const last = candles[candles.length - 1];
  const prev = candles[candles.length - 2] ?? last;
  const change = last.close / prev.close - 1;
  const width = 1280;
  const height = 700;
  const left = 72;
  const right = 34;
  const top = 24;
  const priceHeight = 472;
  const volumeTop = 552;
  const volumeHeight = 102;
  const plotWidth = width - left - right;
  const maxPrice = Math.max(...candles.map((candle) => candle.high));
  const minPrice = Math.min(...candles.map((candle) => candle.low));
  const priceRange = maxPrice - minPrice || 1;
  const maxVolume = Math.max(...candles.map((candle) => candle.volume));
  const step = plotWidth / candles.length;
  const candleWidth = Math.max(5, Math.min(12, step * 0.58));
  const priceY = (value: number) => top + ((maxPrice - value) / priceRange) * priceHeight;
  const volumeY = (value: number) => volumeTop + volumeHeight - (value / maxVolume) * volumeHeight;
  const xFor = (index: number) => left + index * step + step / 2;
  const linePath = (key: "ma5" | "ma20") =>
    candles.map((candle, index) => `${index === 0 ? "M" : "L"} ${xFor(index).toFixed(2)} ${priceY(candle[key]).toFixed(2)}`).join(" ");
  const ticks = Array.from({ length: 6 }, (_, index) => minPrice + (priceRange / 5) * index).reverse();

  return (
    <div className={expanded ? "stock-chart expanded-chart" : "stock-chart"}>
      <div className="stock-chart-header">
        <div>
          <h2>{asset.symbol}</h2>
          <span>{asset.name}</span>
        </div>
        <div className="chart-actions">
          <div className="ohlc-strip">
            <span>시 {formatPrice(last.open, asset)}</span>
            <span>고 {formatPrice(last.high, asset)}</span>
            <span>저 {formatPrice(last.low, asset)}</span>
            <span>종 {formatPrice(last.close, asset)}</span>
            <em className={change >= 0 ? "up" : "down"}>{formatPercent(change)}</em>
          </div>
          {onExpand && (
            <button className="icon-button" onClick={onExpand} title="차트 확대">
              <Expand size={18} />
            </button>
          )}
          {onClose && (
            <button className="icon-button" onClick={onClose} title="닫기">
              <X size={18} />
            </button>
          )}
        </div>
      </div>

      <svg className="candlestick-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${asset.symbol} candlestick chart with volume`}>
        <rect x={left} y={top} width={plotWidth} height={priceHeight} className="chart-bg" />
        <rect x={left} y={volumeTop} width={plotWidth} height={volumeHeight} className="chart-bg" />

        {ticks.map((tick) => {
          const y = priceY(tick);
          return (
            <g key={tick}>
              <line x1={left} x2={width - right} y1={y} y2={y} className="grid-line" />
              <text x={14} y={y + 4} className="axis-label">{formatPrice(tick, asset)}</text>
            </g>
          );
        })}

        {candles.filter((_, index) => index % 12 === 0 || index === candles.length - 1).map((candle) => {
          const realIndex = candles.findIndex((item) => item.date === candle.date);
          const x = xFor(realIndex);
          return (
            <g key={candle.date}>
              <line x1={x} x2={x} y1={top} y2={volumeTop + volumeHeight} className="date-line" />
              <text x={x} y={height - 12} className="date-label">{candle.date}</text>
            </g>
          );
        })}

        <path d={linePath("ma5")} className="ma-line ma5" />
        <path d={linePath("ma20")} className="ma-line ma20" />

        {candles.map((candle, index) => {
          const x = xFor(index);
          const rising = candle.close >= candle.open;
          const yOpen = priceY(candle.open);
          const yClose = priceY(candle.close);
          const bodyY = Math.min(yOpen, yClose);
          const bodyHeight = Math.max(2, Math.abs(yClose - yOpen));
          const colorClass = rising ? "candle-up" : "candle-down";
          const volY = volumeY(candle.volume);
          return (
            <g key={candle.date}>
              <line x1={x} x2={x} y1={priceY(candle.high)} y2={priceY(candle.low)} className={`wick ${colorClass}`} />
              <rect x={x - candleWidth / 2} y={bodyY} width={candleWidth} height={bodyHeight} rx={1.4} className={`candle-body ${colorClass}`} />
              <rect
                x={x - candleWidth / 2}
                y={volY}
                width={candleWidth}
                height={volumeTop + volumeHeight - volY}
                rx={1}
                className={`volume-bar ${colorClass}`}
              />
            </g>
          );
        })}

        <text x={left} y={535} className="volume-label">거래량</text>
        <text x={width - right - 90} y={42} className="legend ma5-text">MA5</text>
        <text x={width - right - 42} y={42} className="legend ma20-text">MA20</text>
      </svg>
    </div>
  );
}

function Quote({ label, value, tone }: { label: string; value: string; tone?: "up" | "down" }) {
  return (
    <div className="quote">
      <span>{label}</span>
      <strong className={tone}>{value}</strong>
    </div>
  );
}

function InfoRow({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="info-row">
      <span>{label}</span>
      <strong className={tone}>{value}</strong>
    </div>
  );
}

function formatPercent(value: number) {
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)}%`;
}

function formatCompact(value: number) {
  return new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

function formatPrice(value: number, asset: Asset) {
  return asset.market === "KR" ? Math.round(value).toLocaleString("en-US") : value.toFixed(2);
}

function tierText(tier: string) {
  if (tier === "core") return "핵심";
  if (tier === "experimental") return "실험";
  return tier;
}

function statusText(status: string) {
  const labels: Record<string, string> = {
    ready: "정상",
    watch: "관찰",
    planned: "예정",
    pass: "통과",
    queued: "대기",
    success: "성공"
  };
  return labels[status] ?? status;
}

createRoot(document.getElementById("root") as HTMLElement).render(<App />);
