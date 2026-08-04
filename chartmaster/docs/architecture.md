# ChartMaster 아키텍처

## v1 방향

ChartMaster는 기존 채용공고 ETL 프로젝트를 대체하는 시장 데이터 기반 MLOps + AI 학습 프로젝트다. 주식 데이터는 정기적으로 갱신되고 데이터 양도 누적되기 때문에, 스케줄 기반 수집, 재학습, 평가, 배포, RAG, 감성 분석, AI 리포트 생성을 연습하기 좋다.

v1의 핵심은 완성된 투자 서비스를 만드는 것이 아니라, 데이터가 수집되고 가공되고 모델 학습으로 이어지는 전체 흐름을 직접 설계하고 설명할 수 있게 만드는 것이다.

## 전체 역할 분리

초기 홈서버 단계에서는 서버1과 서버2의 역할을 나눈다.

```text
서버1
  -> 개발 환경
  -> Airflow 실행
  -> ETL 코드 실행
  -> 모델 학습 실행
  -> FastAPI/Electron 개발

서버2
  -> 파일 저장소
  -> PostgreSQL
  -> 프로젝트별 데이터 영역
```

서버2는 실행 서버가 아니라 데이터 서버로 본다. 나중에 AWS로 확장하면 서버2의 파일 저장소는 S3로, 서버2의 PostgreSQL은 RDS PostgreSQL로 대체된다.

## 시장 데이터 흐름

```text
market data provider
  -> Airflow collection task
  -> raw data storage
  -> feature engineering task
  -> processed feature storage
  -> curated training dataset
  -> model training job
  -> evaluation task
  -> model artifact / prediction result
  -> FastAPI
  -> Electron dashboard
```

초기에는 `yfinance`를 사용해 OHLCV 데이터를 수집한다. 이후 한국장 데이터 품질을 높이고 싶으면 `pykrx` 같은 KRX 중심 데이터 소스로 확장할 수 있다.

## 외부 요인 분석 흐름

```text
news / reports / macro documents
  -> Airflow document collection task
  -> raw document storage
  -> cleaning and chunking
  -> embeddings / vector index
  -> RAG summary
  -> sentiment and event features
  -> FastAPI
  -> Electron dashboard
```

외부 요인 분석은 가격 예측 모델을 대신하지 않는다. 뉴스, 산업 리포트, 매크로 이벤트를 근거로 예측 결과를 해석하는 보조 계층이다.

## 저장소 구조

서버2 파일 저장소는 S3로 옮기기 쉬운 구조로 설계한다.

```text
/home/dnhs02/iwantdataengineer/chartmaster/
  raw/
    market_data/
    external_documents/
  processed/
    features/
    text_features/
  curated/
    training_sets/
  models/
  reports/
  logs/
  backups/
```

각 영역의 의미는 다음과 같다.

- `raw`: 원본 데이터
- `processed`: 피처 생성이 끝난 가공 데이터
- `curated`: 모델 학습에 바로 사용할 최종 데이터셋
- `models`: 학습된 모델 산출물
- `reports`: AI 분석 리포트
- `logs`: ETL 실행 로그
- `backups`: 백업 파일

## PostgreSQL 역할

PostgreSQL은 실제 대용량 파일을 담는 곳이 아니라, 데이터의 위치와 상태를 관리하는 메타데이터 DB로 사용한다.

주요 테이블 후보는 다음과 같다.

- `assets`: 관리 대상 자산 목록
- `pipeline_runs`: ETL/Airflow 실행 이력
- `datasets`: raw/processed/curated 파일 위치와 행 수
- `model_versions`: 모델 버전과 산출물 위치
- `model_metrics`: 모델 평가 지표
- `predictions`: 최신 예측 결과
- `external_documents`: 외부 문서 메타데이터
- `ai_reports`: AI 리포트 메타데이터

핵심은 실제 데이터와 메타데이터를 분리하는 것이다.

```text
파일 저장소 = 실제 데이터 보관
PostgreSQL = 데이터 위치, 상태, 실행 이력 관리
```

## 초기 자산

한국장 core:

- SK하이닉스
- 삼성전자
- 포스코DX
- 현대차

미국장 core:

- Micron Technology
- Western Digital

미국장 experimental:

- SanDisk
- SOXL
- NASA
- SPCX
- RAM

## Core와 Experimental을 나누는 이유

Core 자산은 첫 모델 학습과 평가에 사용할 만큼 데이터 기간이 충분하고 해석이 비교적 쉽다고 가정한다.

Experimental 자산은 데이터 수집과 시각화에는 유용하지만, 다음 이유로 초기 모델 학습에는 약할 수 있다.

- 상장 이력이 짧다.
- 레버리지 ETF는 일일 리셋 구조 때문에 장기 수익률 해석이 어렵다.
- ETF는 여러 기초 자산의 영향을 함께 받는다.

## 첫 모델

첫 모델은 정확한 종가를 예측하지 않는다. 대신 다음 이진 분류 문제로 시작한다.

```text
future_5d_return > 0
```

즉, “5거래일 뒤 수익률이 양수인가?”를 예측한다. 이 방식은 과한 가격 예측을 피하고, 반복 가능한 모델 학습과 평가에 집중하게 해준다.

## AI 계층

AI 기능은 다음 순서로 확장한다.

- Baseline ML: 해석 가능한 기본 모델과 naive baseline부터 시작한다.
- Deep Learning: 기본 파이프라인이 안정된 뒤 LSTM/GRU/Transformer 실험을 추가한다.
- RAG: 관련 뉴스와 문서를 검색해 외부 요인을 설명한다.
- Sentiment Analysis: 뉴스 텍스트를 일별 종목 감성 피처로 변환한다.
- AI Report Generation: 예측 결과, 외부 맥락, 리스크, 데이터 한계를 요약한다.

AI 리포트는 투자 추천이 아니라 모델 결과를 설명하기 위한 학습 산출물이다.
