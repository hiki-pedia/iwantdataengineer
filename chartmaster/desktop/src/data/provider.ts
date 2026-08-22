import type { DashboardDataProvider, DashboardSnapshot, StockCandle } from "./contracts";
import { buildMockCandles, mockAssets, mockSnapshot } from "./mock-data";

class MockDashboardDataProvider implements DashboardDataProvider {
  readonly mode = "mock" as const;

  async loadSnapshot(): Promise<DashboardSnapshot> {
    return mockSnapshot;
  }

  async loadPrices(symbol: string, range: string): Promise<StockCandle[]> {
    const asset = mockAssets.find((candidate) => candidate.symbol === symbol);
    if (!asset) throw new Error(`Unknown asset: ${symbol}`);
    const counts: Record<string, number> = { "ALL": asset.rowCount, "5Y": 1260, "1Y": 252, "6M": 126, "1M": 22, "5D": 5 };
    return buildMockCandles(asset, counts[range] ?? counts["6M"]);
  }
}

class ApiDashboardDataProvider implements DashboardDataProvider {
  readonly mode = "api" as const;

  constructor(private readonly baseUrl: string) {}

  private async get<T>(path: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`);
    if (!response.ok) throw new Error(`API ${response.status}: ${response.statusText}`);
    return response.json() as Promise<T>;
  }

  loadSnapshot(): Promise<DashboardSnapshot> {
    return this.get<DashboardSnapshot>("/api/v1/dashboard");
  }

  loadPrices(symbol: string, range: string): Promise<StockCandle[]> {
    return this.get<StockCandle[]>(`/api/v1/assets/${encodeURIComponent(symbol)}/prices?range=${encodeURIComponent(range)}`);
  }
}

const apiUrl = import.meta.env.VITE_CHARTMASTER_API_URL?.replace(/\/$/, "");

export const dataProvider: DashboardDataProvider = apiUrl
  ? new ApiDashboardDataProvider(apiUrl)
  : new MockDashboardDataProvider();
