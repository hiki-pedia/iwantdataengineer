import { useEffect, useRef, useState } from "react";
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  LineStyle,
  createChart,
  type CandlestickData,
  type MouseEventParams,
  type Time
} from "lightweight-charts";
import type { Asset, ForecastPoint, StockCandle } from "../data/contracts";

type HoverValue = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  x: number;
  y: number;
};

type FinancialChartProps = {
  asset: Asset;
  candles: StockCandle[];
  forecastPoints: ForecastPoint[];
  range: string;
  isDemo: boolean;
  expanded?: boolean;
  onWheelStep: (direction: "in" | "out") => void;
};

const chartColors = {
  background: "#090d14",
  text: "#8793aa",
  grid: "#1c2533",
  up: "#ff4d5f",
  down: "#3b82f6",
  ma5: "#27d7ff",
  ma20: "#ffbd4a",
  forecast: "#d96cff",
  forecastBound: "#8d66b3"
};

export function FinancialChart({ asset, candles, forecastPoints, range, isDemo, expanded, onWheelStep }: FinancialChartProps) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const lastWheelAt = useRef(0);
  const [hover, setHover] = useState<HoverValue | null>(null);

  useEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) return;
    const handleWheel = (event: WheelEvent) => {
      event.preventDefault();
      const now = Date.now();
      if (now - lastWheelAt.current < 320) return;
      lastWheelAt.current = now;
      onWheelStep(event.deltaY < 0 ? "in" : "out");
    };
    wrapper.addEventListener("wheel", handleWheel, { passive: false });
    return () => wrapper.removeEventListener("wheel", handleWheel);
  }, [onWheelStep]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || candles.length === 0) return;

    const chart = createChart(container, {
      width: container.clientWidth,
      height: expanded ? Math.max(620, window.innerHeight - 150) : 620,
      layout: {
        background: { type: ColorType.Solid, color: chartColors.background },
        textColor: chartColors.text,
        attributionLogo: true
      },
      grid: {
        vertLines: { color: chartColors.grid },
        horzLines: { color: chartColors.grid }
      },
      crosshair: { mode: CrosshairMode.Normal },
      localization: { locale: "en-US" },
      rightPriceScale: { borderColor: "#273142" },
      timeScale: {
        borderColor: "#273142",
        timeVisible: false,
        rightOffset: forecastPoints.length > 0 ? 3 : 0
      },
      handleScale: { mouseWheel: false, pinch: true, axisPressedMouseMove: true },
      handleScroll: { mouseWheel: false, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false }
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: chartColors.up,
      downColor: chartColors.down,
      borderVisible: false,
      wickUpColor: chartColors.up,
      wickDownColor: chartColors.down
    });
    candleSeries.setData(candles.map((candle) => ({
      time: candle.date as Time,
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close
    })));

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "volume"
    });
    volumeSeries.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    volumeSeries.setData(candles.map((candle) => ({
      time: candle.date as Time,
      value: candle.volume,
      color: candle.close >= candle.open ? "rgba(255,77,95,0.38)" : "rgba(59,130,246,0.38)"
    })));

    const ma5Series = chart.addSeries(LineSeries, { color: chartColors.ma5, lineWidth: 2, priceLineVisible: false, lastValueVisible: false });
    ma5Series.setData(candles.map((candle) => ({ time: candle.date as Time, value: candle.ma5 })));
    const ma20Series = chart.addSeries(LineSeries, { color: chartColors.ma20, lineWidth: 2, priceLineVisible: false, lastValueVisible: false });
    ma20Series.setData(candles.map((candle) => ({ time: candle.date as Time, value: candle.ma20 })));

    if (forecastPoints.length > 0) {
      const last = candles[candles.length - 1];
      const forecastSeries = chart.addSeries(LineSeries, {
        color: chartColors.forecast,
        lineWidth: 3,
        lineStyle: LineStyle.Dashed,
        priceLineVisible: false,
        title: "예측"
      });
      forecastSeries.setData([
        { time: last.date as Time, value: last.close },
        ...forecastPoints.map((point) => ({ time: point.date as Time, value: point.predictedClose }))
      ]);

      const lowerPoints = forecastPoints.filter((point) => point.lowerBound !== null);
      const upperPoints = forecastPoints.filter((point) => point.upperBound !== null);
      if (lowerPoints.length > 0 && upperPoints.length > 0) {
        const lowerSeries = chart.addSeries(LineSeries, { color: chartColors.forecastBound, lineWidth: 1, lineStyle: LineStyle.Dotted, priceLineVisible: false, lastValueVisible: false });
        const upperSeries = chart.addSeries(LineSeries, { color: chartColors.forecastBound, lineWidth: 1, lineStyle: LineStyle.Dotted, priceLineVisible: false, lastValueVisible: false });
        lowerSeries.setData(lowerPoints.map((point) => ({ time: point.date as Time, value: point.lowerBound as number })));
        upperSeries.setData(upperPoints.map((point) => ({ time: point.date as Time, value: point.upperBound as number })));
      }
    }

    const onCrosshairMove = (param: MouseEventParams<Time>) => {
      if (!param.point || !param.time || param.point.x < 0 || param.point.y < 0 || param.point.x > container.clientWidth || param.point.y > container.clientHeight) {
        setHover(null);
        return;
      }
      const candle = param.seriesData.get(candleSeries) as CandlestickData<Time> | undefined;
      if (!candle || !("open" in candle)) {
        setHover(null);
        return;
      }
      const date = formatTime(param.time);
      const source = candles.find((item) => item.date === date);
      setHover({
        date,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
        volume: source?.volume ?? 0,
        x: Math.min(param.point.x + 14, Math.max(12, container.clientWidth - 230)),
        y: Math.max(12, param.point.y - 72)
      });
    };
    chart.subscribeCrosshairMove(onCrosshairMove);
    chart.timeScale().fitContent();

    const resizeObserver = new ResizeObserver(([entry]) => {
      chart.applyOptions({ width: Math.floor(entry.contentRect.width) });
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.unsubscribeCrosshairMove(onCrosshairMove);
      chart.remove();
    };
  }, [asset.symbol, candles, expanded, forecastPoints]);

  return (
    <div className="financial-chart" ref={wrapperRef}>
      <div className="financial-chart-meta">
        <div><strong>{asset.symbol}</strong><span>{asset.name}</span></div>
        <div className="chart-legend"><span className="ma5-key">MA5</span><span className="ma20-key">MA20</span>{forecastPoints.length > 0 && <span className="forecast-key">예측선</span>}</div>
        <em>{range}{isDemo ? " · DEMO SERIES" : ""}</em>
      </div>
      <div className="financial-chart-canvas" ref={containerRef} />
      {hover && (
        <div className="chart-tooltip" style={{ left: hover.x, top: hover.y }}>
          <strong>{hover.date}</strong>
          <span>시 {formatPrice(hover.open, asset)}</span><span>고 {formatPrice(hover.high, asset)}</span>
          <span>저 {formatPrice(hover.low, asset)}</span><span>종 {formatPrice(hover.close, asset)}</span>
          <small>거래량 {formatCompact(hover.volume)}</small>
        </div>
      )}
    </div>
  );
}

function formatTime(time: Time) {
  if (typeof time === "string") return time;
  if (typeof time === "number") return new Date(time * 1000).toISOString().slice(0, 10);
  return `${time.year}-${String(time.month).padStart(2, "0")}-${String(time.day).padStart(2, "0")}`;
}

function formatPrice(value: number, asset: Asset) {
  return asset.market === "KR" ? Math.round(value).toLocaleString("en-US") : value.toFixed(2);
}

function formatCompact(value: number) {
  return new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}
