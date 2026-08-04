# ChartMaster 학습 로드맵

## Phase 1: 로컬 시장 데이터 기준선과 서버2 저장 구조

- 초기 자산 목록의 과거 OHLCV 데이터를 수집한다.
- 서버2에 ChartMaster 전용 파일 저장소를 만든다.
- raw, processed, curated, models, reports, logs, backups 영역을 분리한다.
- 가격, 거래량, 거래대금, 변동성, 모멘텀 기반 기본 피처를 만든다.
- 서버2 PostgreSQL에 실행 이력과 데이터셋 메타데이터를 저장한다.

학습 포인트:

- `yfinance` 사용법
- OHLCV 데이터 구조
- raw 데이터와 processed 데이터 분리
- 파일 저장소와 DB 역할 분리
- metadata DB 설계
- 로컬 환경에서 S3/RDS 역할 이해

## Phase 2: Airflow 로컬 자동화

- `daily_kr_market_data_etl` DAG를 만든다.
- `daily_us_market_data_etl` DAG를 만든다.
- 한국장과 미국장 장마감 시간을 분리해서 스케줄링한다.
- Task 로그, 실패, 재시도 동작을 확인한다.
- 서버가 꺼져 있던 동안 놓친 실행은 Airflow catchup으로 복구한다.
- 10일 overlap 수집과 날짜 기준 merge/dedup으로 누락과 데이터 정정을 흡수한다.

학습 포인트:

- Airflow DAG
- Task 의존성
- 스케줄 실행
- 실패와 retry
- catchup
- Docker Compose 운영

## Phase 3: Electron Dashboard UI 설계와 Mock Prototype

- 실제 모델, RAG, 리포트가 완성되기 전에 먼저 앱 화면 구조를 설계한다.
- Dashboard, Assets, Asset Detail, Pipelines, Models, Reports, Settings 화면을 만든다.
- mock JSON을 이용해 화면 상태와 데이터 표시 방식을 검증한다.
- 나중에 FastAPI가 반환할 응답 형태를 mock data shape으로 먼저 고정한다.
- 데이터 품질과 모델 정확도에 의존하지 않는 UI/UX 결정을 먼저 끝낸다.

학습 포인트:

- Electron 데스크톱 앱 구조
- 화면 정보 구조 설계
- mock data 기반 UI 개발
- 차트/테이블/상태 뷰 구성
- 나중에 바뀌기 어려운 사용자 흐름 먼저 고정하기

## Phase 4: FastAPI 계약과 Mock-to-Live 연결 준비

- Electron 앱이 직접 서버2 파일 저장소나 PostgreSQL에 접근하지 않도록 FastAPI 계층을 둔다.
- Phase 3의 mock JSON과 동일한 형태의 API response contract를 정의한다.
- 초기에는 mock provider를 반환하고, 이후 server2/PostgreSQL provider로 교체할 수 있게 만든다.
- 종목 목록, 데이터 범위, 파이프라인 상태, 모델 metric, 리포트 조회 API를 정의한다.

학습 포인트:

- FastAPI
- API contract
- mock provider와 live provider 분리
- Electron과 backend 연결
- 화면 요구사항에서 API를 역설계하기

## Phase 5: 종목 유니버스와 데이터 소스 검증

- 국내장과 미국장 종목 수를 늘린 결과를 검증한다.
- 섹터, 시가총액, 거래량, 상장 기간을 기준으로 종목군을 나눈다.
- yfinance, pykrx 등 데이터 소스별 커버리지와 한계를 비교한다.
- 상장 이력이 짧은 ETF/신규 종목은 experimental tier로 분리한다.
- 종목 수가 늘어나도 raw/processed/metadata 구조가 유지되는지 확인한다.

학습 포인트:

- 자산 유니버스 설계
- 데이터 소스 검증
- coverage gap
- 백필 전략
- 대량 종목 수집 시 rate limit과 실패 처리

## Phase 6: 로컬 모델 학습과 평가 기준선

- processed feature 데이터를 이용해 첫 baseline 모델을 학습한다.
- 5거래일 뒤 상승 여부, 다음 날 수익률 등 문제 정의를 비교한다.
- naive baseline과 비교한다.
- 모델 artifact와 평가 metric을 서버2에 저장한다.
- PostgreSQL에는 모델 버전, metric, 산출물 위치를 기록한다.

학습 포인트:

- 기본 피처 엔지니어링
- train/validation split
- time series split
- Accuracy, Precision, Recall, F1-score
- 모델 artifact
- 모델 메타데이터 관리

## Phase 7: 모델 재학습 자동화와 배포 후보 등록

- `weekly_model_training` DAG를 만든다.
- Airflow에서 모델 학습, 평가, artifact 저장을 자동화한다.
- validation 기준을 통과한 모델만 배포 후보로 등록한다.
- 통과/실패한 모델 버전을 기록한다.

학습 포인트:

- Airflow 학습 파이프라인
- 모델 평가 자동화
- 조건부 배포
- 모델 버전 관리
- 재현 가능한 학습 실행

## Phase 8: AI/RAG 외부 요인 계층

- 뉴스, 리포트, 매크로 이벤트 문서를 수집한다.
- 외부 문서는 시장 데이터와 별도로 raw 영역에 저장한다.
- 검색 연습을 위한 간단한 vector index를 만든다.
- RAG 기반 외부 요인 요약을 생성한다.
- 감성 점수와 이벤트 유형 피처를 만든다.

학습 포인트:

- RAG
- 문서 chunking
- embedding
- vector index
- sentiment feature
- 외부 요인과 가격 데이터 결합

## Phase 9: 딥러닝 실험

- rolling price window 기반 LSTM 또는 GRU 모델을 학습한다.
- 기본 ML 모델과 딥러닝 모델 성능을 비교한다.
- 과적합 여부와 validation 안정성을 확인한다.
- 딥러닝은 첫 기준 모델이 아니라 비교 실험으로 둔다.

학습 포인트:

- 시계열 window
- LSTM/GRU
- Transformer 기반 시계열 모델
- overfitting
- 모델 비교 실험

## Phase 10: AI 리포트 생성

- 예측 결과, 모델 metric, RAG 요약, 감성 피처를 조합한다.
- 사람이 읽을 수 있는 일별 종목 리포트를 생성한다.
- 투자 추천 문구가 들어가지 않도록 guardrail을 둔다.

학습 포인트:

- LLM 기반 요약
- 근거 기반 리포트 생성
- hallucination 방지
- 투자 조언과 분석 설명의 차이

## Phase 11: AWS S3 Data Lake와 RDS 이전

- 서버2 파일 저장소 구조를 S3 bucket 구조로 이전한다.
- 서버2 PostgreSQL 메타데이터 DB를 RDS PostgreSQL로 이전한다.
- provider, symbol, date/year 기준 파티션 구조를 유지한다.
- 기존 `ssh://` 또는 local path 기반 `storage_uri`를 `s3://` URI 구조로 바꾼다.

학습 포인트:

- S3 bucket
- object storage
- data lake
- RDS PostgreSQL
- IAM과 보안 그룹
- local path와 `s3://` URI 전환

## Phase 12: SageMaker 학습과 운영 관찰성

- Airflow에서 SageMaker Training Job을 실행한다.
- S3의 processed feature 데이터를 읽어 학습한다.
- 모델 산출물과 평가 지표를 다시 S3/RDS에 기록한다.
- CloudWatch 로그, 실패 알림, 재시도 정책, 백업 정책을 확인한다.

학습 포인트:

- SageMaker Training Job
- managed training
- Airflow와 AWS 서비스 연동
- CloudWatch
- 운영 관찰성

## 학습 기록 템플릿

- 날짜:
- 오늘 목표:
- 사용한 데이터 소스:
- 배운 개념:
- 실행한 명령어:
- 구현 결과:
- 실패한 점:
- 해결 방법:
- 포트폴리오에서 설명할 문장:
