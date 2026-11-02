import { useEffect, useRef } from "react";
import { CandlestickSeries, ColorType, LineSeries, LineStyle, createChart, type Time } from "lightweight-charts";
import type { Asset, Prediction, StockCandle } from "../data/contracts";

type PredictionSignalChartProps = {
  asset: Asset;
  candles: StockCandle[];
  prediction?: Prediction;
};

const WINDOW_SIZE = 40;

export function PredictionSignalChart({ asset, candles, prediction }: PredictionSignalChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const probability = prediction?.upProbability ?? null;
  const isReady = prediction?.status === "ready" || prediction?.status === "stale";

  useEffect(() => {
    const container = containerRef.current;
    if (!container || candles.length === 0 || !isReady) return;

    const recent = candles.slice(-WINDOW_SIZE);
    const chart = createChart(container, {
      width: container.clientWidth,
      height: 250,
      layout: { background: { type: ColorType.Solid, color: "#090d14" }, textColor: "#7f8ba2", attributionLogo: true },
      grid: { vertLines: { color: "#17202d" }, horzLines: { color: "#17202d" } },
      rightPriceScale: { borderColor: "#273142", minimumWidth: 58 },
      timeScale: {
        borderColor: "#273142",
        rightOffset: prediction?.forecastPoints.length ? 2 : 0,
        timeVisible: false,
        fixLeftEdge: true,
        fixRightEdge: true
      },
      handleScale: false,
      handleScroll: false
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#ff4d5f",
      downColor: "#3b82f6",
      borderVisible: false,
      wickUpColor: "#ff4d5f",
      wickDownColor: "#3b82f6",
      priceLineVisible: true,
      lastValueVisible: true
    });
    candleSeries.setData(recent.map((candle) => ({
      time: candle.date as Time,
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close
    })));

    const ma5 = chart.addSeries(LineSeries, { color: "#27d7ff", lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
    ma5.setData(recent.map((candle) => ({ time: candle.date as Time, value: candle.ma5 })));
    const ma20 = chart.addSeries(LineSeries, { color: "#ffbd4a", lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
    ma20.setData(recent.map((candle) => ({ time: candle.date as Time, value: candle.ma20 })));

    if (prediction?.forecastPoints.length) {
      const last = recent[recent.length - 1];
      const forecast = chart.addSeries(LineSeries, {
        color: "#d96cff",
        lineWidth: 3,
        lineStyle: LineStyle.Dashed,
        priceLineVisible: false,
        lastValueVisible: true,
        title: "방향"
      });
      forecast.setData([
        { time: last.date as Time, value: last.close },
        ...prediction.forecastPoints.map((point) => ({ time: point.date as Time, value: point.predictedClose }))
      ]);

      const lower = prediction.forecastPoints.filter((point) => point.lowerBound !== null);
      const upper = prediction.forecastPoints.filter((point) => point.upperBound !== null);
      if (lower.length && upper.length) {
        const options = { color: "#74568f", lineWidth: 1 as const, lineStyle: LineStyle.Dotted, priceLineVisible: false, lastValueVisible: false };
        const lowerSeries = chart.addSeries(LineSeries, options);
        const upperSeries = chart.addSeries(LineSeries, options);
        lowerSeries.setData(lower.map((point) => ({ time: point.date as Time, value: point.lowerBound as number })));
        upperSeries.setData(upper.map((point) => ({ time: point.date as Time, value: point.upperBound as number })));
      }
    }

    chart.timeScale().fitContent();
    const resizeObserver = new ResizeObserver(([entry]) => chart.applyOptions({ width: Math.floor(entry.contentRect.width) }));
    resizeObserver.observe(container);
    return () => {
      resizeObserver.disconnect();
      chart.remove();
    };
  }, [asset.symbol, candles, isReady, prediction]);

  return (
    <section className="prediction-signal" aria-label="최근 구간 5거래일 방향 예측 그래프">
      <div className="prediction-signal-heading">
        <div><strong>최근 구간 예측</strong><span>최근 {Math.min(WINDOW_SIZE, candles.length)}거래일 확대</span></div>
        <em className={prediction?.predictedDirection === "up" ? "up" : "down"}>
          {prediction?.predictedDirection === "up" ? "상승 판정" : prediction?.predictedDirection === "down" ? "하락 판정" : "대기"}
        </em>
      </div>
      {isReady && probability !== null ? (
        <>
          <div className="prediction-probabilities">
            <span className="up">상승 {formatPercent(probability)}</span>
            <span className="down">하락 {formatPercent(1 - probability)}</span>
          </div>
          <div className="prediction-mini-chart" ref={containerRef} />
          <div className="prediction-mini-legend">
            <span className="ma5-key">MA5</span><span className="ma20-key">MA20</span><span className="forecast-key">5일 방향 시나리오</span>
          </div>
          <p>목표가격이 아닌 방향 확률의 시각화입니다.</p>
        </>
      ) : <div className="prediction-empty">예측 결과가 아직 준비되지 않았습니다.</div>}
    </section>
  );
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}
