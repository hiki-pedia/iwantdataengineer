# ChartMaster Desktop

Electron과 React로 만든 ChartMaster 로컬 클라이언트다. Electron은 서버2 파일이나 PostgreSQL에 직접 연결하지 않고 서버1 FastAPI만 호출한다.

## 현재 상태

- 29개 자산 레지스트리 표시
- 2026-08-22에 확인한 Server 2 품질 결과를 Mock 스냅샷으로 표시
- 차트 시계열은 `DEMO SERIES`로 명시
- 차트 호버에서 날짜, OHLCV 표시
- `ALL / 5Y / 1Y / 6M / 1M / 5D` 기간 버튼과 휠 단계 전환
- 전체 이력을 유지한 상태에서 기간을 확대하고 과거 구간으로 이동
- 데이터 검증 화면에서 종목별 오류·경고 코드, 설명, 영향 행 수와 검사일 표시
- 모델이 없으므로 예측 확률을 생성하지 않고 `model_not_ready`로 표시
- `VITE_CHARTMASTER_API_URL`이 있으면 API provider, 없으면 Mock provider 사용

FastAPI가 서버2의 실제 파일 저장소를 읽어 대시보드와 가격 데이터를 제공한다. API URL을 설정했는데 연결에 실패하면 Mock으로 자동 전환하지 않고 오류를 표시한다. 운영 연결 문제를 가짜 데이터로 숨기지 않기 위한 동작이다.

## 실제 데이터 연결

서버1에서 API 컨테이너를 실행한다.

```bash
cd /home/dnhs01/iwantdataengineer/chartmaster
docker compose --env-file ../.env up -d --build chartmaster-api
curl http://127.0.0.1:8000/health
```

로컬 PC의 `chartmaster/desktop/.env.local`에 서버1 주소를 지정한다.

```dotenv
VITE_CHARTMASTER_API_URL=http://192.168.0.5:8000
```

로컬 PC와 서버1이 서로 다른 네트워크에 있다면 `192.168.0.5` 대신 로컬 PC에서 접근 가능한 서버1의 WireGuard 주소를 사용한다.

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
  "uncertaintyNote": "학습과 시간순 검증이 끝난 모델이 없어 확률을 제공하지 않습니다.",
  "forecastPoints": []
}
```

실제 확률을 제공할 때는 모델 버전, 학습 데이터 기준일, 평가 지표와 데이터 품질을 함께 반환해야 한다.

차트의 예측 연장선은 `forecastPoints`가 있을 때만 표시한다. 각 점은 미래 거래일의 예측 종가와 선택적인 하한·상한을 제공한다.

```json
{
  "date": "2026-08-24",
  "predictedClose": 285000,
  "lowerBound": 278000,
  "upperBound": 292000
}
```

현재 정의한 방향성 분류 모델은 상승 확률만 출력하므로 위 가격 경로를 직접 만들 수 없다. 예측선을 실제로 제공하려면 일별 수익률 또는 가격 경로를 출력하는 별도 모델과 검증 지표가 필요하다.
