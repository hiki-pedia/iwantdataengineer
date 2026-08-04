# ChartMaster 기술 명세서

## 1. 시스템 개요

ChartMaster는 Electron 데스크톱 앱, FastAPI 백엔드, Airflow 워크플로우, PostgreSQL 메타데이터 DB, 서버2 파일 저장소, 이후 AWS S3/RDS/SageMaker 확장 흐름, RAG/AI 분석 계층으로 구성한다.

v1의 핵심은 “데이터 수집부터 모델 학습과 평가까지 자동화된 파이프라인”을 만드는 것이다. AI 계층은 가격 예측 모델의 결과를 해석하고 외부 요인을 정리하는 보조 계층으로 둔다.

## 2. 전체 아키텍처

```text
Electron Desktop Application
  -> FastAPI Backend
    -> PostgreSQL metadata
    -> S3 processed data
    -> model prediction result
    -> AI report result

Airflow
  -> collect market data
  -> write S3 raw data
  -> build features
  -> write S3 processed data
  -> collect external documents/news
  -> build sentiment/RAG signals
  -> trigger model training
  -> evaluate model
  -> register/deploy model if accepted
  -> generate AI report
```

초기 로컬 단계에서는 S3와 SageMaker를 바로 붙이지 않는다. 먼저 서버2 파일 저장소와 PostgreSQL을 이용해 raw/processed 저장 구조와 Airflow 자동화를 만든다. 그 다음에는 데이터 품질과 모델링이 안정되기를 기다리기보다, Electron Dashboard UI와 FastAPI 응답 계약을 mock data 기반으로 먼저 고정한다. 이후 종목 유니버스 검증, 로컬 모델 학습, RAG/AI 리포트, AWS 이전 순서로 확장한다.

## 3. 기술 스택

| 영역 | 기술 | 역할 |
| --- | --- | --- |
| Desktop | Electron | 사용자가 보는 데스크톱 앱 |
| Backend API | FastAPI | 앱과 데이터/모델 결과를 연결 |
| Workflow | Apache Airflow | ETL, 학습, 평가 작업 스케줄링 |
| Metadata DB | PostgreSQL | 자산, 실행 이력, 모델 메타데이터 저장 |
| Object Storage | Amazon S3 | 원천 데이터, 피처, 모델 산출물 저장 |
| ML Training | SageMaker | 모델 학습과 배포 자동화 |
| Local ML | Python, pandas, scikit-learn | 초기 모델링과 로컬 검증 |
| Deep Learning | PyTorch 또는 TensorFlow | LSTM/Transformer 계열 시계열 모델 실험 |
| LLM/RAG | OpenAI API, vector store | 뉴스/문서 요약과 외부 요인 분석 |
| Infra | Docker Compose | 로컬 개발 환경 실행 |

## 4. 데이터 수집

초기 데이터 제공자는 `yfinance` 또는 공개 OHLCV 제공자를 사용할 수 있다. 단, 특정 제공자에 코드가 강하게 묶이지 않도록 provider 계층을 분리한다.

한국장 데이터 품질이 부족할 경우 이후 단계에서 `pykrx` 또는 KRX 중심 데이터 소스로 확장한다.

### 필수 원천 필드

- date
- open
- high
- low
- close
- adjusted_close
- volume

### 수집 주기

v1 기본 수집 주기는 일 1회다. 한국장과 미국장의 장 마감 시간이 다르므로 실제 운영 단계에서는 시장별 실행 시간을 분리할 수 있다.

초기 학습 단계에서는 다음 방식으로 시작한다.

- 매일 정해진 시간에 전체 자산 데이터 갱신
- 누락된 날짜만 추가 수집
- 같은 날짜 데이터가 중복 저장되지 않도록 처리

## 5. 저장 구조

### 5.1 S3 저장 경로

AWS 적용 후에는 다음 구조를 기본으로 사용한다.

```text
s3://chartmaster-{env}/raw/market_data/{provider}/{symbol}/date=YYYY-MM-DD/
s3://chartmaster-{env}/raw/external_documents/{source}/date=YYYY-MM-DD/
s3://chartmaster-{env}/processed/features/{symbol}/as_of=YYYY-MM-DD/
s3://chartmaster-{env}/processed/text_features/{symbol}/as_of=YYYY-MM-DD/
s3://chartmaster-{env}/models/{model_name}/{version}/
s3://chartmaster-{env}/metrics/{model_name}/{version}/
s3://chartmaster-{env}/reports/{symbol}/as_of=YYYY-MM-DD/
```

### 5.2 PostgreSQL 역할

PostgreSQL은 대용량 시계열 원천 데이터를 모두 담는 저장소라기보다, 앱과 파이프라인 운영에 필요한 메타데이터를 관리하는 역할로 둔다.

주요 테이블 후보는 다음과 같다.

| 테이블 | 역할 |
| --- | --- |
| `assets` | 관리 대상 자산 목록 |
| `pipeline_runs` | Airflow 또는 ETL 실행 이력 |
| `model_versions` | 모델 버전, 학습일, 산출물 위치 |
| `model_metrics` | 모델 평가 지표 |
| `predictions` | 최신 예측 결과 |
| `external_documents` | 수집한 뉴스/문서 메타데이터 |
| `external_factor_summaries` | RAG 기반 외부 요인 요약 |
| `ai_reports` | AI 분석 리포트 스냅샷 |

## 6. 자산 레지스트리

초기 자산 레지스트리는 다음 파일에서 관리한다.

```text
config/assets.json
```

각 자산은 다음 필드를 가진다.

- symbol
- display_name
- market
- exchange
- asset_type
- group
- modeling_tier
- notes

`modeling_tier`는 `core`와 `experimental`로 구분한다. `core`는 초기 모델 학습 대상이고, `experimental`은 먼저 수집과 시각화 중심으로 검증한다.

## 7. 피처 엔지니어링

v1에서 사용할 기본 피처는 가격, 거래량, 거래대금, 모멘텀, 변동성 중심으로 구성한다.

### 파생 필드

- `turnover_value = close * volume`
- `return_1d`
- `return_5d`
- `return_20d`
- `volume_change_1d`
- `moving_average_5`
- `moving_average_20`
- `volatility_5`
- `volatility_20`

### 피처 생성 원칙

미래 데이터를 현재 시점의 피처에 섞지 않는다. 모든 피처는 예측 기준일 이전 또는 당일 확정 데이터만 사용해야 한다.

## 8. 모델 설계

### 8.1 초기 예측 대상

초기 모델의 타깃은 다음과 같다.

```text
target_positive_5d_return = future_5d_return > 0
```

즉, 특정 기준일로부터 5거래일 뒤 수익률이 양수인지 예측하는 이진 분류 문제다.

### 8.2 초기 모델 후보

v1에서는 복잡한 딥러닝보다 기준선과 비교하기 쉬운 모델부터 사용한다.

- Naive baseline
- Logistic Regression
- Random Forest
- Gradient Boosting 계열 모델

딥러닝 모델은 기본 ML 파이프라인이 안정된 뒤 비교 실험으로 추가한다.

- LSTM
- GRU
- 1D CNN
- Transformer 기반 시계열 모델
- Temporal Fusion Transformer 또는 PatchTST 계열 모델

### 8.3 평가 지표

초기 평가 지표는 다음과 같다.

- Accuracy
- Precision
- Recall
- F1-score
- ROC-AUC

클래스 불균형이 심한 경우 Accuracy보다 F1-score와 Precision/Recall을 우선해서 본다.

### 8.4 배포 조건

모델은 무조건 배포하지 않는다. 다음 조건을 만족할 때만 배포 후보로 등록한다.

```text
validation f1 >= configured threshold
and
validation f1 > naive baseline f1
```

## 9. AI/RAG 설계

ChartMaster의 AI 기능은 크게 세 가지 역할로 나눈다.

1. 외부 요인 검색과 요약
2. 뉴스 감성/이벤트 신호 생성
3. 예측 결과 설명 리포트 생성

### 9.1 문서 수집 대상

초기 수집 대상은 다음과 같다.

- 종목 관련 뉴스
- 산업 뉴스
- 기업 공시 또는 실적 발표 요약
- 금리, 환율, CPI, FOMC 등 매크로 이벤트 문서

각 문서는 최소한 다음 메타데이터를 가진다.

- source
- url
- title
- published_at
- related_symbols
- raw_text
- collected_at

### 9.2 RAG 흐름

```text
collect_external_documents
  -> clean_documents
  -> chunk_documents
  -> embed_chunks
  -> store_vector_index
  -> retrieve_relevant_context
  -> generate_factor_summary
```

RAG 결과는 가격 예측 모델의 정답처럼 취급하지 않는다. 모델 결과를 해석하는 설명 자료로 사용한다.

### 9.3 감성 분석 흐름

```text
news document
  -> sentiment classifier
  -> sentiment_score
  -> event_type classifier
  -> daily_symbol_sentiment_features
```

감성 분석 결과는 다음 피처로 저장할 수 있다.

- `news_positive_count`
- `news_negative_count`
- `news_neutral_count`
- `news_sentiment_score`
- `macro_risk_score`
- `sector_sentiment_score`

### 9.4 AI 리포트 생성

AI 리포트는 다음 입력을 조합해 생성한다.

- 최신 예측 결과
- 최근 주요 피처
- 모델 평가 지표
- RAG 기반 외부 요인 요약
- 감성 분석 점수

출력은 다음 구조를 따른다.

```text
summary
key_market_factors
model_signal
risk_notes
data_limitations
```

리포트에는 투자 추천 표현을 넣지 않는다.

## 10. Airflow DAG 설계

최종적으로는 다음 DAG를 분리해서 운영한다.

| DAG | 역할 |
| --- | --- |
| `daily_market_data_etl` | 일별 시장 데이터 수집과 피처 생성 |
| `daily_external_factor_etl` | 뉴스/문서 수집, 감성 분석, RAG 인덱스 갱신 |
| `weekly_model_training` | 주기적 모델 학습 |
| `model_evaluation_and_deploy` | 모델 평가와 배포 후보 등록 |
| `daily_ai_report_generation` | 최신 예측과 외부 요인을 묶은 AI 리포트 생성 |

학습 초기에는 하나의 DAG에서 전체 흐름을 연결하고, 구조가 안정되면 DAG를 분리한다.

### 10.1 `daily_market_data_etl`

```text
load_asset_registry
  -> collect_market_data
  -> validate_raw_data
  -> write_raw_data
  -> build_features
  -> validate_features
  -> write_processed_features
  -> update_metadata
```

### 10.2 `daily_external_factor_etl`

```text
collect_external_documents
  -> clean_documents
  -> classify_sentiment
  -> classify_event_type
  -> update_vector_index
  -> write_external_factor_features
```

### 10.3 `weekly_model_training`

```text
load_training_dataset
  -> split_train_validation
  -> train_model
  -> write_model_artifact
  -> write_training_metadata
```

### 10.4 `model_evaluation_and_deploy`

```text
load_candidate_model
  -> evaluate_model
  -> compare_with_baseline
  -> register_model_if_accepted
  -> update_prediction_snapshot
```

### 10.5 `daily_ai_report_generation`

```text
load_latest_prediction
  -> load_latest_features
  -> retrieve_external_context
  -> generate_ai_report
  -> write_report_snapshot
```

## 11. AWS 연동 계획

AWS는 한 번에 붙이지 않고 단계적으로 붙인다.

### Phase 1: Local Server Platform

- Docker Compose 기반 Airflow 실행
- 서버2 파일 저장소에 raw/processed/model/report 데이터 저장
- 서버2 PostgreSQL에 데이터셋과 실행 이력 metadata 저장

### Phase 2: App Contract Prototype

- Electron Dashboard mock prototype 작성
- Dashboard, Assets, Asset Detail, Pipelines, Models, Reports 화면 설계
- mock JSON 기반 UI 상태 검증
- FastAPI response contract 정의

### Phase 3: Local Data and MLOps

- 국내장/미국장 종목 유니버스 검증
- 데이터 소스 커버리지와 품질 확인
- 로컬 Python 모델 학습
- Airflow에서 모델 재학습 DAG 실행
- 모델 버전과 metric 기록
- RAG/감성 피처와 딥러닝 실험을 로컬 구조에서 검증

### Phase 4: S3/RDS

- raw 데이터 S3 저장
- processed 피처 S3 저장
- 모델 산출물 S3 저장
- 서버2 PostgreSQL metadata를 RDS PostgreSQL로 이전

### Phase 5: SageMaker

- Airflow에서 SageMaker Training Job 실행
- 학습 산출물을 S3에 저장
- 평가 결과를 PostgreSQL과 S3에 기록

### Phase 6: 운영 관찰성

- CloudWatch 로그 확인
- 실패 알림
- 재시도 정책
- 백업 정책

## 12. FastAPI 인터페이스

Electron 앱은 직접 DB나 S3에 접근하지 않고 FastAPI를 통해 데이터를 조회한다.

초기 API 후보는 다음과 같다.

| Method | Path | 역할 |
| --- | --- | --- |
| `GET` | `/assets` | 자산 목록 조회 |
| `GET` | `/assets/{symbol}/prices` | 가격/거래량 데이터 조회 |
| `GET` | `/assets/{symbol}/features/latest` | 최신 피처 조회 |
| `GET` | `/assets/{symbol}/prediction/latest` | 최신 예측 결과 조회 |
| `GET` | `/models` | 모델 버전 목록 조회 |
| `GET` | `/pipeline/runs` | 파이프라인 실행 이력 조회 |
| `GET` | `/assets/{symbol}/external-factors/latest` | 최신 외부 요인 요약 조회 |
| `GET` | `/assets/{symbol}/ai-report/latest` | 최신 AI 분석 리포트 조회 |

## 13. 리스크와 제약

- 주가는 뉴스, 심리, 금리, 환율, 유동성 등 외부 요인의 영향을 크게 받는다.
- OHLCV만으로 높은 예측 성능을 기대하기 어렵다.
- `SOXL`, `RAM` 같은 레버리지 ETF는 일일 리셋 구조 때문에 장기 해석이 어렵다.
- `RAM`, `NASA`, `SPCX`처럼 이력이 짧거나 데이터 소스가 불안정한 자산은 모델 학습에 부적합할 수 있다.
- ETF는 여러 기초 자산이 섞여 있어 개별 주식보다 설명 가능성이 낮다.
- RAG 요약은 원문 품질과 검색 결과에 영향을 받는다.
- LLM 리포트는 근거 없는 단정을 만들 수 있으므로 출처와 제한 사항을 함께 표시해야 한다.
- 딥러닝 모델은 데이터가 부족하면 단순 모델보다 쉽게 과적합된다.

따라서 v1의 목표는 “수익성 있는 모델”이 아니라 “자동화된 데이터/모델 파이프라인을 만들고 검증하는 것”이다.

## 14. 검증 계획

v1 구현 후 다음을 확인한다.

1. Airflow DAG가 수동 실행과 스케줄 실행에서 정상 동작한다.
2. 같은 날짜의 데이터가 중복 저장되지 않는다.
3. 수집 데이터에 필수 필드가 모두 존재한다.
4. 피처 생성 시 미래 데이터 누수가 없다.
5. 모델 학습 결과가 저장된다.
6. 기준선 모델과 성능 비교가 가능하다.
7. 배포 조건을 통과한 모델만 등록된다.
8. 외부 문서 수집 결과가 중복 없이 저장된다.
9. RAG 요약이 관련 문서 근거를 포함한다.
10. AI 리포트가 투자 추천 표현 없이 생성된다.
11. Electron 앱에서 최신 예측 결과와 모델 이력을 조회할 수 있다.
