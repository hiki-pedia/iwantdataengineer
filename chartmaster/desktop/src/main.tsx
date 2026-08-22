import React, { useEffect, useState } from "react";
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
import type { Asset, DashboardSnapshot, Prediction, StockCandle } from "./data/contracts";
import { dataProvider } from "./data/provider";
import { FinancialChart } from "./components/FinancialChart";
import "./styles.css";

type AppRoute = `asset:${string}` | "dashboard" | "assets" | "data-status" | "data-check" | "events" | "predictions" | "pipelines" | "reports";
const RANGE_OPTIONS = ["ALL", "5Y", "1Y", "6M", "1M", "5D"] as const;
type ChartRange = (typeof RANGE_OPTIONS)[number];

function App() {
  const [route, setRoute] = useState<AppRoute>("dashboard");
  const [isExpanded, setIsExpanded] = useState(false);
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    dataProvider.loadSnapshot().then(setSnapshot).catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : "데이터를 불러오지 못했습니다.");
    });
  }, []);

  useEffect(() => {
    document.querySelector("main")?.scrollTo({ top: 0, left: 0 });
    setIsExpanded(false);
  }, [route]);

  if (error) {
    return <SystemState title="데이터 연결 실패" detail={error} />;
  }
  if (!snapshot) {
    return <SystemState title="데이터 불러오는 중" detail="Dashboard provider 응답을 기다리고 있습니다." />;
  }

  const selectedSymbol = route.startsWith("asset:") ? route.slice("asset:".length) : snapshot.assets[0].symbol;
  const selectedAsset = snapshot.assets.find((asset) => asset.symbol === selectedSymbol) ?? snapshot.assets[0];
  const selectedPrediction = snapshot.predictions.find((prediction) => prediction.symbol === selectedAsset.symbol);

  return (
    <div className="shell">
      <Sidebar route={route} setRoute={setRoute} />
      <main>
        <div className={`source-banner ${snapshot.sourceMode}`}>
          <strong>{snapshot.sourceMode === "api" ? "LIVE API" : "MOCK SNAPSHOT"}</strong>
          <span>{snapshot.sourceLabel}</span>
          <time>{formatDateTime(snapshot.generatedAt)}</time>
        </div>
        {route === "dashboard" && <DashboardPage snapshot={snapshot} setRoute={setRoute} />}
        {route === "assets" && <AssetsPage assets={snapshot.assets} setRoute={setRoute} />}
        {route.startsWith("asset:") && (
          <AssetPage
            asset={selectedAsset}
            prediction={selectedPrediction}
            sourceMode={snapshot.sourceMode}
            isExpanded={isExpanded}
            setIsExpanded={setIsExpanded}
          />
        )}
        {route === "data-status" && <DataStatusPage assets={snapshot.assets} />}
        {route === "data-check" && <DataCheckPage checks={snapshot.dataChecks} />}
        {route === "events" && <EventsPage events={snapshot.events} setRoute={setRoute} />}
        {route === "predictions" && <PredictionsPage assets={snapshot.assets} predictions={snapshot.predictions} setRoute={setRoute} />}
        {route === "pipelines" && <PipelinesPage assets={snapshot.assets} runs={snapshot.pipelineRuns} setRoute={setRoute} />}
        {route === "reports" && <ReportsPage assets={snapshot.assets} reports={snapshot.reports} setRoute={setRoute} />}
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

      <NavSection title="시장">
        <NavButton active={route === "dashboard"} icon={<BarChart3 size={16} />} label="대시보드" onClick={() => setRoute("dashboard")} />
        <NavButton active={route === "assets" || route.startsWith("asset:")} icon={<LineChart size={16} />} label="종목" onClick={() => setRoute("assets")} />
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

function SystemState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="system-state">
      <Database size={28} />
      <strong>{title}</strong>
      <span>{detail}</span>
    </div>
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

function DashboardPage({ snapshot, setRoute }: { snapshot: DashboardSnapshot; setRoute: (route: AppRoute) => void }) {
  const krCount = snapshot.assets.filter((asset) => asset.market === "KR").length;
  const warningCount = snapshot.assets.filter((asset) => asset.dataStatus === "watch").length;
  const movers = [...snapshot.assets].sort((left, right) => Math.abs(right.return1d ?? 0) - Math.abs(left.return1d ?? 0)).slice(0, 6);
  return (
    <Page title="대시보드" icon={<BarChart3 />}>
      <section className="quote-strip summary-strip">
        <Quote label="전체 자산" value={snapshot.assets.length.toString()} />
        <Quote label="한국 / 미국" value={`${krCount} / ${snapshot.assets.length - krCount}`} />
        <Quote label="품질 관찰" value={`${warningCount}종목`} tone={warningCount ? "watch" : "up"} />
        <Quote label="예측 모델" value="미준비" />
      </section>
      <section className="dashboard-band">
        <div className="section-heading"><h2>주요 변동</h2><span>최근 스냅샷 기준</span></div>
        <div className="asset-table">
          {movers.map((asset) => (
            <button key={asset.symbol} onClick={() => setRoute(`asset:${asset.symbol}`)}>
              <strong>{asset.symbol}</strong><span>{asset.name}</span>
              <em className={(asset.return1d ?? 0) >= 0 ? "up" : "down"}>{formatNullablePercent(asset.return1d)}</em>
              <small>{statusText(asset.dataStatus)}</small>
            </button>
          ))}
        </div>
      </section>
    </Page>
  );
}

function AssetsPage({ assets, setRoute }: { assets: Asset[]; setRoute: (route: AppRoute) => void }) {
  const [query, setQuery] = useState("");
  const [market, setMarket] = useState<"ALL" | "KR" | "US">("ALL");
  const filtered = assets.filter((asset) => {
    const matchesMarket = market === "ALL" || asset.market === market;
    const needle = query.trim().toLowerCase();
    return matchesMarket && (!needle || asset.symbol.toLowerCase().includes(needle) || asset.name.toLowerCase().includes(needle));
  });
  return (
    <Page title="종목" icon={<LineChart />}>
      <div className="asset-toolbar">
        <div className="segmented-control">
          {(["ALL", "KR", "US"] as const).map((value) => (
            <button className={market === value ? "active" : ""} key={value} onClick={() => setMarket(value)}>{value}</button>
          ))}
        </div>
        <input aria-label="종목 검색" placeholder="티커 또는 종목명 검색" value={query} onChange={(event) => setQuery(event.target.value)} />
      </div>
      <div className="asset-table asset-directory">
        {filtered.map((asset) => (
          <button key={asset.symbol} onClick={() => setRoute(`asset:${asset.symbol}`)}>
            <strong>{asset.symbol}</strong><span>{asset.name}</span><span>{asset.market} · {asset.assetType}</span>
            <em className={(asset.return1d ?? 0) >= 0 ? "up" : "down"}>{formatNullablePercent(asset.return1d)}</em>
            <small className={asset.dataStatus}>{statusText(asset.dataStatus)}</small>
          </button>
        ))}
      </div>
    </Page>
  );
}

function AssetPage({
  asset,
  prediction,
  sourceMode,
  isExpanded,
  setIsExpanded
}: {
  asset: Asset;
  prediction?: Prediction;
  sourceMode: DashboardSnapshot["sourceMode"];
  isExpanded: boolean;
  setIsExpanded: (value: boolean) => void;
}) {
  const [candles, setCandles] = useState<StockCandle[]>([]);
  const [priceError, setPriceError] = useState<string | null>(null);
  const [range, setRange] = useState<ChartRange>("5Y");

  useEffect(() => {
    setCandles([]);
    setPriceError(null);
    dataProvider.loadPrices(asset.symbol, "ALL").then(setCandles).catch((reason: unknown) => {
      setPriceError(reason instanceof Error ? reason.message : "가격 데이터를 불러오지 못했습니다.");
    });
  }, [asset.symbol]);

  const stepRange = (direction: "in" | "out") => {
    const current = RANGE_OPTIONS.indexOf(range);
    const next = direction === "in" ? Math.min(current + 1, RANGE_OPTIONS.length - 1) : Math.max(current - 1, 0);
    setRange(RANGE_OPTIONS[next]);
  };

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
        <Quote label="종가" value={formatNullablePrice(asset.latestClose, asset)} />
        <Quote label="1D" value={formatNullablePercent(asset.return1d)} tone={(asset.return1d ?? 0) >= 0 ? "up" : "down"} />
        <Quote label="거래량" value={formatNullableCompact(asset.volume)} />
        <Quote label="데이터 기간" value={`${asset.startDate} - ${asset.endDate}`} />
      </section>

      <section className="asset-layout">
        <div className="chart-panel">
          <div className="chart-toolbar">
            <div className="segmented-control range-control">
              {RANGE_OPTIONS.map((option) => (
                <button className={range === option ? "active" : ""} key={option} onClick={() => setRange(option)}>{option}</button>
              ))}
            </div>
            <button className="icon-button" onClick={() => setIsExpanded(true)} title="차트 확대"><Expand size={18} /></button>
          </div>
          {priceError && <SystemState title="가격 데이터 오류" detail={priceError} />}
          {!priceError && candles.length === 0 && <SystemState title="차트 불러오는 중" detail={asset.symbol} />}
          {candles.length > 0 && (
            <FinancialChart
              asset={asset}
              candles={candles}
              forecastPoints={prediction?.forecastPoints ?? []}
              range={range}
              isDemo={sourceMode === "mock"}
              onWheelStep={stepRange}
            />
          )}
        </div>
        <aside className="inspector">
          <h2>데이터</h2>
          <InfoRow label="행 수" value={asset.rowCount.toLocaleString()} />
          <InfoRow label="최신 일자" value={asset.endDate} />
          <InfoRow label="품질" value={asset.warningCount ? `경고 ${asset.warningCount}` : "통과"} tone={asset.warningCount ? "watch" : "ready"} />
          <InfoRow label="표시 소스" value={sourceMode === "mock" ? "스냅샷 / 데모" : "Live API"} />
          <InfoRow label="등급" value={tierText(asset.tier)} />
          <h2>예측</h2>
          <InfoRow label="예측 기간" value={`${prediction?.horizonTradingDays ?? 5} 거래일`} />
          <InfoRow label="상태" value={predictionStatusText(prediction?.status)} tone={prediction?.status === "ready" ? "ready" : "watch"} />
          <InfoRow label="상승 확률" value={formatProbability(prediction?.upProbability)} />
          <InfoRow label="모델" value={prediction?.modelVersion ?? "-"} />
        </aside>
      </section>

      {isExpanded && (
        <div className="chart-overlay">
          <div className="chart-modal">
            <button className="icon-button modal-close" onClick={() => setIsExpanded(false)} title="닫기"><X size={18} /></button>
            <FinancialChart
              asset={asset}
              candles={candles}
              forecastPoints={prediction?.forecastPoints ?? []}
              range={range}
              isDemo={sourceMode === "mock"}
              expanded
              onWheelStep={stepRange}
            />
          </div>
        </div>
      )}
    </section>
  );
}

function DataStatusPage({ assets }: { assets: Asset[] }) {
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
            <InfoRow label="품질 경고" value={asset.warningCount.toString()} tone={asset.warningCount ? "watch" : "ready"} />
          </article>
        ))}
      </section>
    </Page>
  );
}

function DataCheckPage({ checks }: { checks: DashboardSnapshot["dataChecks"] }) {
  return (
    <Page title="데이터 검증" icon={<SearchCheck />}>
      <section className="panel-list">
        {checks.map((check) => (
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

function EventsPage({ events, setRoute }: { events: DashboardSnapshot["events"]; setRoute: (route: AppRoute) => void }) {
  return (
    <Page title="이벤트" icon={<AlertTriangle />}>
      <section className="panel-list">
        {events.map((event) => (
          <button className="event-row" key={`${event.symbol}-${event.date}`} onClick={() => setRoute(`asset:${event.symbol}`)}>
            <strong>{event.symbol}</strong>
            <span>{event.date}</span>
            <span>{event.type}</span>
            <em className={event.move >= 0 ? "up" : "down"}>{formatPercent(event.move)}</em>
            <span>{event.causeSummary ?? "외부 근거 분석 전"}</span>
          </button>
        ))}
      </section>
    </Page>
  );
}

function PredictionsPage({ assets, predictions, setRoute }: { assets: Asset[]; predictions: Prediction[]; setRoute: (route: AppRoute) => void }) {
  const [query, setQuery] = useState("");
  const [market, setMarket] = useState<"ALL" | "KR" | "US">("ALL");
  const filtered = filterAssets(assets, market, query);
  return (
    <Page title="예측" icon={<Brain />}>
      <AssetFilterBar market={market} query={query} onMarket={setMarket} onQuery={setQuery} />
      <div className="entity-table prediction-table">
        <div className="entity-table-head"><span>종목</span><span>시장</span><span>기준일</span><span>기간</span><span>상승 확률</span><span>모델 상태</span></div>
        {filtered.map((asset) => {
          const prediction = predictions.find((item) => item.symbol === asset.symbol);
          return (
            <button key={asset.symbol} onClick={() => setRoute(`asset:${asset.symbol}`)}>
              <span className="entity-name"><strong>{asset.symbol}</strong><small>{asset.name}</small></span>
              <span>{asset.market}</span><span>{prediction?.asOf ?? "-"}</span>
              <span>{prediction?.horizonTradingDays ?? 5}거래일</span>
              <em className={prediction?.status === "ready" ? "up" : "watch"}>{formatProbability(prediction?.upProbability)}</em>
              <span className={prediction?.status === "ready" ? "ready" : "watch"}>{predictionStatusText(prediction?.status)}</span>
            </button>
          );
        })}
      </div>
    </Page>
  );
}

function PipelinesPage({ assets, runs, setRoute }: { assets: Asset[]; runs: DashboardSnapshot["pipelineRuns"]; setRoute: (route: AppRoute) => void }) {
  const [query, setQuery] = useState("");
  const [market, setMarket] = useState<"ALL" | "KR" | "US">("ALL");
  const filtered = filterAssets(assets, market, query);
  return (
    <Page title="파이프라인" icon={<Workflow />}>
      <section className="status-grid pipeline-grid">
        {runs.map((run) => (
          <article className="status-card" key={run.name}>
            <div>
              <strong>{run.name}</strong>
              <span>{run.lastRun ?? "실행 이력 없음"}</span>
            </div>
            <em className={run.status}>{statusText(run.status)}</em>
            <InfoRow label="다음 실행" value={run.nextRun ?? "-"} />
            <InfoRow label="행 수" value={run.rows.toLocaleString()} />
          </article>
        ))}
      </section>
      <div className="section-heading pipeline-heading"><h2>종목별 최신 데이터</h2><span>DAG Task 상태가 아닌 최종 데이터 기준</span></div>
      <AssetFilterBar market={market} query={query} onMarket={setMarket} onQuery={setQuery} />
      <div className="entity-table pipeline-asset-table">
        <div className="entity-table-head"><span>종목</span><span>시장</span><span>수집 DAG</span><span>최신 일자</span><span>행 수</span><span>품질</span></div>
        {filtered.map((asset) => (
          <button key={asset.symbol} onClick={() => setRoute(`asset:${asset.symbol}`)}>
            <span className="entity-name"><strong>{asset.symbol}</strong><small>{asset.name}</small></span>
            <span>{asset.market}</span><span>{asset.market === "KR" ? "daily_kr_market_data_etl" : "daily_us_market_data_etl"}</span>
            <span>{asset.endDate}</span><span>{asset.rowCount.toLocaleString()}</span>
            <span className={asset.dataStatus}>{asset.warningCount ? `경고 ${asset.warningCount}` : "통과"}</span>
          </button>
        ))}
      </div>
    </Page>
  );
}

function ReportsPage({ assets, reports, setRoute }: { assets: Asset[]; reports: DashboardSnapshot["reports"]; setRoute: (route: AppRoute) => void }) {
  const [query, setQuery] = useState("");
  const [market, setMarket] = useState<"ALL" | "KR" | "US">("ALL");
  const filtered = filterAssets(assets, market, query);
  return (
    <Page title="리포트" icon={<FileText />}>
      <AssetFilterBar market={market} query={query} onMarket={setMarket} onQuery={setQuery} />
      <div className="entity-table report-table">
        <div className="entity-table-head"><span>종목</span><span>시장</span><span>시장 요약</span><span>외부 요인</span><span>모델 평가</span><span>최근 생성</span></div>
        {filtered.map((asset) => {
          const assetReport = reports.find((report) => report.symbol === asset.symbol);
          return (
            <button key={asset.symbol} onClick={() => setRoute(`asset:${asset.symbol}`)}>
              <span className="entity-name"><strong>{asset.symbol}</strong><small>{asset.name}</small></span>
              <span>{asset.market}</span><span className="planned">예정</span><span className="planned">예정</span><span className="planned">예정</span>
              <span>{assetReport?.date ?? "생성 전"}</span>
            </button>
          );
        })}
      </div>
    </Page>
  );
}

function AssetFilterBar({
  market,
  query,
  onMarket,
  onQuery
}: {
  market: "ALL" | "KR" | "US";
  query: string;
  onMarket: (market: "ALL" | "KR" | "US") => void;
  onQuery: (query: string) => void;
}) {
  return (
    <div className="asset-toolbar">
      <div className="segmented-control">
        {(["ALL", "KR", "US"] as const).map((value) => (
          <button className={market === value ? "active" : ""} key={value} onClick={() => onMarket(value)}>{value}</button>
        ))}
      </div>
      <input aria-label="종목 검색" placeholder="티커 또는 종목명 검색" value={query} onChange={(event) => onQuery(event.target.value)} />
    </div>
  );
}

function filterAssets(assets: Asset[], market: "ALL" | "KR" | "US", query: string) {
  const needle = query.trim().toLowerCase();
  return assets.filter((asset) => {
    const matchesMarket = market === "ALL" || asset.market === market;
    return matchesMarket && (!needle || asset.symbol.toLowerCase().includes(needle) || asset.name.toLowerCase().includes(needle));
  });
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

function Quote({ label, value, tone }: { label: string; value: string; tone?: "up" | "down" | "watch" }) {
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

function formatNullableCompact(value: number | null) {
  return value === null ? "-" : formatCompact(value);
}

function formatPrice(value: number, asset: Asset) {
  return asset.market === "KR" ? Math.round(value).toLocaleString("en-US") : value.toFixed(2);
}

function formatNullablePrice(value: number | null, asset: Asset) {
  return value === null ? "-" : formatPrice(value, asset);
}

function formatNullablePercent(value: number | null) {
  return value === null ? "-" : formatPercent(value);
}

function formatProbability(value: number | null | undefined) {
  return value == null ? "제공 안 함" : `${(value * 100).toFixed(1)}%`;
}

function formatDateTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function predictionStatusText(status: Prediction["status"] | undefined) {
  const labels: Record<Prediction["status"], string> = {
    model_not_ready: "모델 미준비",
    ready: "예측 생성 완료",
    stale: "예측 갱신 필요",
    failed: "예측 실패"
  };
  return status ? labels[status] : "예측 없음";
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
    success: "성공",
    running: "실행 중",
    failed: "실패",
    unavailable: "사용 불가"
  };
  return labels[status] ?? status;
}

createRoot(document.getElementById("root") as HTMLElement).render(<App />);
