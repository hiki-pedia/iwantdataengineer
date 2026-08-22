# ChartMaster Desktop

Electron과 React로 만든 ChartMaster 로컬 클라이언트다. Electron은 서버2 파일이나 PostgreSQL에 직접 연결하지 않고, 향후 서버1 FastAPI만 호출한다.

## 현재 상태

- 29개 자산 레지스트리 표시
- 2026-08-22에 확인한 Server 2 품질 결과를 Mock 스냅샷으로 표시
- 차트 시계열은 `DEMO SERIES`로 명시
- 모델이 없으므로 예측 확률을 생성하지 않고 `model_not_ready`로 표시
- `VITE_CHARTMASTER_API_URL`이 있으면 API provider, 없으면 Mock provider 사용

현재 FastAPI는 아직 구현하지 않았다. API URL을 설정했는데 연결에 실패하면 Mock으로 자동 전환하지 않고 오류를 표시한다. 운영 연결 문제를 가짜 데이터로 숨기지 않기 위한 동작이다.

## 실행 환경

Electron 43 개발 도구는 Node.js 22.12 이상을 사용한다.

```bash
cd chartmaster/desktop
npm ci
npm run dev
```

Electron 창은 다른 터미널에서 실행한다.

```bash
cd chartmaster/desktop
npm run electron
```

## Provider 계약

데이터 계약은 `src/data/contracts.ts`, 구현체는 `src/data/provider.ts`에 있다.

API provider가 사용할 엔드포인트:

```text
GET /api/v1/dashboard
GET /api/v1/assets/{symbol}/prices?range=6M
```

`/api/v1/dashboard`는 자산, 품질 검사, 파이프라인 실행, 이벤트, 예측, 리포트 상태를 포함한 `DashboardSnapshot`을 반환한다. 가격 API는 날짜순 `StockCandle[]`을 반환한다.

## 예측 계약

첫 모델의 문제는 기준일 데이터로 5거래일 뒤 상승 여부를 예측하는 이진 분류다. 모델 학습과 시간순 검증 전에는 다음 상태를 반환한다.

```json
{
  "symbol": "005930.KS",
  "asOf": "2026-08-21",
  "targetDate": null,
  "horizonTradingDays": 5,
  "status": "model_not_ready",
  "predictedDirection": null,
  "upProbability": null,
  "modelVersion": null,
  "trainedThrough": null,
  "dataQuality": "watch",
  "metricSummary": null,
  "uncertaintyNote": "학습과 시간순 검증이 끝난 모델이 없어 확률을 제공하지 않습니다."
}
```

실제 확률을 제공할 때는 모델 버전, 학습 데이터 기준일, 평가 지표와 데이터 품질을 함께 반환해야 한다.
