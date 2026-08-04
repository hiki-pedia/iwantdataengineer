# Electron Dashboard 설계 메모

이 문서는 ChartMaster Phase 3에서 만들 Electron Dashboard의 화면 구성과 설계 방향을 정리한 문서다.

Phase 3의 목적은 실제 모델, RAG, AI 리포트가 완성되기 전에 먼저 앱의 화면 구조와 정보 흐름을 고정하는 것이다. 데이터 품질 검증, 모델링, RAG는 계속 바뀔 수 있으므로, 먼저 나중에도 크게 바뀌지 않을 화면과 API 계약을 mock data 기반으로 만든다.

## 1. Phase 3 목표

```text
Electron 앱에서 시장 데이터, 종목 차트, 급등/급락 이벤트, 예측 결과, Airflow 파이프라인 상태를 볼 수 있는 화면 구조를 mock data 기반으로 설계한다.
```

핵심은 다음과 같다.

- 실제 데이터 연결보다 화면 구조를 먼저 정한다.
- 모델 결과가 없어도 예측 화면의 자리를 만든다.
- RAG가 없어도 급등/급락 원인 분석 화면의 자리를 만든다.
- FastAPI가 나중에 어떤 형태로 응답해야 하는지 mock data shape으로 먼저 정한다.
- Electron 앱이 직접 서버2 파일 저장소나 PostgreSQL에 접근하지 않는 구조를 전제로 한다.

## 2. 전체 디자인 방향

전체적인 시각 스타일은 어두운 금융 터미널 느낌으로 잡는다.

```text
배경:
  black / near-black

텍스트:
  white / gray 계열

차트:
  neon cyan
  neon green
  electric blue
  magenta
  red/orange warning color

분위기:
  차분하지만 기술적인 대시보드
  데이터가 많은 화면도 읽기 쉬운 구조
  장식보다 정보 밀도와 상태 파악을 우선
```

차트 색상 후보:

```text
가격 라인:
  cyan 또는 lime

거래량:
  muted violet 또는 blue-gray

급등 이벤트:
  neon green marker

급락 이벤트:
  neon red marker

예측 구간:
  electric blue 또는 magenta
```

## 3. 앱 실행 구조

Electron 앱은 로컬 PC에 설치 가능한 클라이언트로 만든다.

```text
로컬 PC
  -> Electron App 실행
  -> 서버1 FastAPI 호출

서버1
  -> FastAPI Backend
  -> Airflow 실행
  -> ETL 코드 실행
  -> 서버2 접근

서버2
  -> raw/processed 파일 저장
  -> PostgreSQL metadata 저장
```

초기 Phase 3에서는 FastAPI 없이 mock data를 사용한다.

```text
Phase 3
Electron UI
  -> mock JSON

Phase 4
Electron UI
  -> FastAPI
  -> 서버2 PostgreSQL / 파일 저장소
```

## 4. 주요 화면 구조

추천 메뉴 구조는 다음과 같다.

```text
Dashboard
Assets
Asset Detail
Events
Predictions
Airflow / Pipelines
Reports
Settings
```

Phase 3에서 우선 구현할 화면:

```text
1. Dashboard
2. Assets
3. Asset Detail
4. Events
5. Airflow / Pipelines
```

Phase 3에서 mock 자리만 잡을 화면:

```text
6. Predictions
7. Reports
8. Settings
```

## 5. Dashboard 화면

앱을 켰을 때 가장 먼저 보는 화면이다.

보여줄 정보:

```text
전체 자산 수
한국장 자산 수
미국장 자산 수
최신 데이터 기준일
가장 많이 오른 종목 TOP 5
가장 많이 내린 종목 TOP 5
거래량 급증 종목
변동성 높은 종목
최근 Airflow 수집 상태
서버2 / PostgreSQL 연결 상태
```

목적:

- 시장 전체 상태를 빠르게 파악한다.
- 데이터 수집이 정상인지 확인한다.
- 어떤 종목을 더 자세히 봐야 하는지 힌트를 준다.

## 6. Assets 화면

관리 대상 종목 목록을 보여주는 화면이다.

필터:

```text
시장:
  KR / US

자산 유형:
  stock / ETF / leveraged ETF

모델링 등급:
  core / experimental

섹터 또는 그룹:
  semiconductor
  financial
  energy
  consumer
  technology
  utilities
  automotive
  etc.

검색:
  ticker
  name
```

정렬:

```text
상승률
하락률
거래량
변동성
데이터 시작일
row count
```

목록에서 보여줄 기본 컬럼:

```text
symbol
display_name
market
asset_type
group
modeling_tier
start_date
end_date
row_count
latest_return_1d
latest_volume
```

## 7. Asset Detail 화면

종목별 상세 분석 화면이다.

필수 구성:

```text
종목 기본 정보
가격 차트
거래량 차트
기간 선택
기본 지표 요약
급등/급락 이벤트 마커
예측 결과 카드
관련 리포트 링크
```

기간 선택:

```text
1M
3M
6M
1Y
5Y
ALL
```

차트 옵션:

```text
종가
거래량
MA5
MA20
MA60
급등/급락 이벤트 표시
예측 구간 표시
```

기본 지표:

```text
1D return
5D return
20D return
YTD return
volatility_20d
volume_change_1d
turnover_value
latest_close
```

## 8. Events 화면

급등/급락이 왜 일어났는지 보는 화면이다.

이 화면은 ChartMaster를 단순 차트 앱이 아니라 AI 분석 프로젝트로 만드는 핵심 화면이다.

보여줄 정보:

```text
event_id
symbol
event_date
event_type
daily_return
volume_change
price_change_5d
severity
cause_summary
cause_candidates
confidence
related_news
related_report
```

이벤트 유형:

```text
sharp_rise
sharp_drop
volume_spike
volatility_spike
earnings_related
macro_related
industry_related
unknown
```

원인 후보:

```text
실적 발표
금리
환율
업황
경쟁사 이슈
규제
전쟁/공급망
ETF 리밸런싱
기업 공시
원인 미확인
```

초기 Phase 3에서는 실제 RAG 분석 대신 mock 원인 후보를 보여준다. 이후 Phase 8에서 뉴스/RAG/감성 분석과 연결한다.

## 9. Predictions 화면

예측 결과를 보여주는 화면이다.

주의:

이 화면은 투자 추천 화면이 아니다. 매수/매도 같은 표현은 사용하지 않는다.

사용할 표현:

```text
상승 가능성
하락 가능성
모델 신호
불확실성
참고용 분석
```

보여줄 정보:

```text
symbol
prediction_date
horizon
up_probability
down_probability
confidence
model_version
model_metric_summary
top_features
uncertainty_note
```

예측 기간:

```text
1D
5D
20D
```

Phase 3에서는 mock prediction을 사용하고, 실제 모델은 Phase 6 이후 연결한다.

## 10. Airflow / Pipelines 화면

Airflow는 별도 페이지로 구성한다.

앱 안에서는 Airflow 운영 상태 요약을 보여주고, 상세 로그와 Graph/Grid 화면은 기존 Airflow UI로 이동할 수 있게 한다.

보여줄 DAG:

```text
daily_kr_market_data_etl
daily_us_market_data_etl
weekly_model_training
```

현재 Phase 3에서는 `weekly_model_training`은 mock 또는 planned 상태로 둔다.

보여줄 정보:

```text
dag_id
status
last_run_at
next_run_at
duration_seconds
success_count
failed_count
retry_count
collected_assets
written_rows
latest_log_summary
```

상태:

```text
success
running
failed
queued
paused
planned
unknown
```

추가 기능:

```text
Open Airflow UI 버튼
최근 실행 이력 목록
실패 task 강조
서버 재시작 후 catchup 실행 여부 표시
```

Airflow UI 연결:

```text
http://server1:8081
```

## 11. Reports 화면

AI 리포트와 이벤트 리포트를 보는 화면이다.

Phase 3에서는 mock report를 사용하고, 실제 리포트 생성은 Phase 10에서 붙인다.

보여줄 정보:

```text
report_id
symbol
report_date
title
summary
market_context
event_summary
prediction_summary
source_count
created_at
```

리포트 유형:

```text
daily_asset_report
market_summary
event_explanation
model_summary
rag_external_factor_summary
```

주의 문구:

```text
이 리포트는 투자 조언이 아니라 데이터 엔지니어링과 모델링 학습을 위한 분석 결과입니다.
```

## 12. Settings 화면

연결 정보와 앱 설정을 관리하는 화면이다.

보여줄 정보:

```text
API base URL
server1 status
server2 storage status
PostgreSQL metadata status
Airflow UI URL
theme mode
data refresh interval
app version
```

초기 Phase 3에서는 mock status를 보여준다.

## 13. Mock Data

mock data는 실제 서버, DB, 모델, RAG가 없어도 화면을 만들기 위해 사용하는 가짜 JSON 데이터다.

예를 들어 실제 예측 모델이 없어도 예측 화면은 먼저 만들 수 있다.

```json
{
  "symbol": "005930.KS",
  "prediction_date": "2026-08-04",
  "horizon": "5d",
  "up_probability": 0.62,
  "down_probability": 0.38,
  "confidence": "medium",
  "model_version": "mock-baseline-v0"
}
```

mock data를 쓰는 이유:

```text
화면 개발을 데이터/모델 개발과 분리할 수 있다.
어떤 정보가 필요한지 먼저 알 수 있다.
나중에 FastAPI가 같은 모양으로 진짜 데이터를 주면 쉽게 교체할 수 있다.
모델/RAG가 없어도 예측/리포트 화면을 미리 만들 수 있다.
```

mock data는 버리는 가짜가 아니라, 이후 FastAPI 응답 계약의 초안이다.

## 14. Mock JSON 후보

Phase 3에서 둘 mock 파일:

```text
mock/assets.json
mock/market_summary.json
mock/price_series.json
mock/events.json
mock/predictions.json
mock/airflow_runs.json
mock/reports.json
mock/settings.json
```

예시: Airflow run

```json
{
  "dag_id": "daily_kr_market_data_etl",
  "status": "success",
  "last_run_at": "2026-08-04T16:10:00+09:00",
  "duration_seconds": 42,
  "collected_assets": 12,
  "written_rows": 120,
  "retry_count": 0
}
```

예시: Event

```json
{
  "event_id": "evt-aapl-2026-07-31-drop",
  "symbol": "AAPL",
  "event_date": "2026-07-31",
  "event_type": "sharp_drop",
  "daily_return": -0.058,
  "volume_change": 2.4,
  "severity": "high",
  "cause_summary": "Mock explanation for a large move.",
  "cause_candidates": ["earnings_related", "macro_related"],
  "confidence": "low"
}
```

## 15. Phase 3 산출물

Phase 3가 끝났을 때 있어야 하는 것:

```text
Electron 프로젝트 기본 구조
dark/neon dashboard theme
sidebar navigation
Dashboard 화면
Assets 화면
Asset Detail 화면
Events 화면
Airflow / Pipelines 화면
Predictions / Reports / Settings placeholder
mock JSON 파일들
나중에 FastAPI로 교체 가능한 data access 구조
```

## 16. 다음 Phase와 연결

Phase 4에서는 Electron mock data를 FastAPI contract로 바꾼다.

```text
Phase 3
Electron UI -> mock JSON

Phase 4
Electron UI -> FastAPI mock provider

이후
Electron UI -> FastAPI live provider -> 서버2 PostgreSQL / 파일 저장소
```

즉 Phase 3에서 정한 mock data shape은 Phase 4의 API 응답 형태가 된다.
