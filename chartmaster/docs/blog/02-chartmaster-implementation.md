---
title: "ChartMaster: Airflow와 AWS를 활용한 주식 데이터 기반 AI 분석 시스템"
date: 2026-08-15 09:00:00 +0900
categories:
  - projects
tags:
  - personal-project
  - data-engineering
  - airflow
  - docker
  - postgresql
  - stock-data
  - mlops
project_group: personal
project_order: 2
project_list_title: "Airflow와 AWS를 활용한 주식 데이터 기반 AI 분석 시스템"
---

## 프로젝트 개요

ChartMaster는 한국·미국 시장의 주식 데이터를 이용해 데이터 수집부터 저장, 가공, 모델 학습, 외부 요인 분석, 서비스 제공까지 하나의 흐름으로 연결해보는 개인 데이터·인프라 프로젝트다.

단순히 주가를 수집해 차트를 그리거나 예측 모델 하나를 만드는 것이 목적은 아니다. 시장 데이터가 매일 추가되는 환경에서 다음 문제를 직접 해결하는 것이 프로젝트의 중심이다.

- 데이터를 정해진 시간에 반복해서 수집할 수 있는가?
- 서버가 꺼져 있거나 네트워크 장애가 발생해도 누락 데이터를 복구할 수 있는가?
- 원본 데이터와 가공 데이터, 모델 산출물을 목적에 맞게 분리할 수 있는가?
- 어떤 실행이 어떤 데이터 파일을 만들었는지 추적할 수 있는가?
- 모델 학습 결과와 외부 뉴스·문서를 하나의 분석 흐름으로 연결할 수 있는가?
- 로컬 홈서버에서 검증한 구조를 AWS 관리형 서비스로 이전할 수 있는가?

이를 위해 두 대의 Ubuntu 홈서버를 실행 계층과 데이터 계층으로 나누고, Python ETL, Airflow, PostgreSQL, Docker를 단계적으로 연결하고 있다. 로컬 구조가 안정되면 Electron과 FastAPI를 이용해 결과를 제공하고, 이후 저장소와 학습 환경을 S3, RDS, SageMaker로 확장할 계획이다.

현재는 Phase 1과 Phase 3을 완료했고 Phase 2 자동 수집을 운영하고 있다. Phase 5 데이터 품질과 재처리도 최신 운영 검증까지 마무리했다. 진행 중간에 이후 모델·RAG·리포트 결과가 들어갈 화면과 API 계약을 먼저 고정하기 위해 Phase 3 Electron Dashboard와 Phase 4 FastAPI 핵심 조회 계층을 구현했다. 이 글은 프로젝트가 끝난 뒤 작성하는 결과 보고서가 아니라, 각 Phase에서 세운 목표와 구현 내용, 해결한 문제, 아직 남은 과제를 계속 추가하는 개발 기록이다.

| 항목 | 현재 상태 |
| --- | --- |
| 데이터 소스 | yfinance |
| 관리 자산 | 한국·미국 주식 및 ETF 29개 |
| 실행 환경 | Ubuntu 홈서버 2대, Docker Compose |
| 오케스트레이션 | Apache Airflow 2.10.5, LocalExecutor |
| 파일 저장소 | Server 2의 SSH 파일 저장소 |
| 메타데이터 DB | Server 2의 PostgreSQL 16 |
| 구현 범위 | Phase 1·3·5 완료, Phase 2 운영 중, Phase 4 핵심 연결 구현 |
| 현재 작업 | Phase 6 운영 안정성과 백업/복구 설계 준비 |

> 이 프로젝트의 예측 결과와 분석 결과는 데이터 엔지니어링 및 MLOps 학습을 위한 산출물이며 투자 추천을 목적으로 하지 않는다.

## 프로젝트를 시작한 이유

처음에는 채용공고 데이터를 대상으로 ETL 프로젝트를 구성하려 했다. 하지만 일정 기간이 지나면 데이터 구조와 처리 방식이 반복되고, 모델 재학습이나 외부 요인 분석까지 확장하기에는 학습 범위가 제한적이라고 판단했다.

주식 시장 데이터는 매일 새로운 값이 추가되고 한국장과 미국장의 거래 시간이 다르다. 신규 상장 종목은 과거 데이터가 짧고, 데이터 제공자가 이전 값을 수정하거나 특정 날짜를 늦게 제공하는 경우도 있다. 여기에 기업 실적, 금리, 환율, 산업 이슈, 정책 변화 같은 외부 문서까지 연결할 수 있다.

이런 특성은 단순 수집 이외에도 다음 주제를 계속 확장해보기 적합했다.

```text
정기 수집과 백필
  -> 누락·중복 처리
  -> Raw / Processed / Curated 저장 계층
  -> 실행 및 데이터셋 메타데이터
  -> 모델 학습과 평가 이력
  -> 뉴스·리포트 기반 외부 요인 분석
  -> API와 데스크톱 대시보드
  -> AWS 관리형 서비스 이전
```

따라서 ChartMaster의 첫 번째 목표는 높은 예측 정확도가 아니다. 데이터와 실행 이력을 다시 확인할 수 있고, 같은 작업을 재실행해도 데이터가 망가지지 않으며, 장애 이후에도 복구 가능한 파이프라인을 만드는 것이 우선이다.

## 전체 Phase 계획

프로젝트는 한 번에 모든 기술을 붙이지 않고, 앞 단계의 산출물을 다음 단계가 실제로 사용하도록 순서를 나눴다.

| Phase | 주제 | 구현 목표 | 상태 |
| --- | --- | --- | --- |
| 1 | 로컬 시장 데이터 기준선 | 자산 레지스트리, 과거 OHLCV 백필, SSH 파일 저장소, 피처 생성, PostgreSQL 메타데이터 | 완료 |
| 2 | Airflow 로컬 자동화 | 한국장·미국장 DAG, Catchup, 10일 Overlap, Merge/Dedup, Retry | 운영 중 |
| 3 | Electron Dashboard Mock | 화면 정보 구조를 만들고 Mock JSON으로 API 응답 형태 확정 | 완료 |
| 4 | FastAPI 서비스 계층 | Electron과 파일·DB 사이의 API 경계 및 Mock/Live Provider 구현 | 핵심 연결 구현 |
| 5 | 데이터 품질과 재처리 | Coverage, 누락, 중복, 날짜 범위 검사와 백필·재처리 절차 구현 | 완료 |
| 6 | 운영 안정성과 복구 | 파일·DB 백업, 복원 훈련, Airflow 장애 대응, 모니터링 | 계획 |
| 7 | 머신러닝 파이프라인 | Baseline 모델, 시계열 분할, 평가 지표와 모델 버전 기록 | 계획 |
| 8 | RAG와 외부 요인 분석 | 뉴스·리포트 수집, Chunking, 검색, 감성·이벤트 피처와 AI 리포트 | 계획 |
| 9 | AWS 저장 계층 이전 | 로컬 파일 저장소와 PostgreSQL을 S3와 RDS로 이전 | 계획 |
| 10 | AWS 학습과 관찰성 | SageMaker Training Job, CloudWatch 로그·지표·비용 점검 | 계획 |

Phase 순서는 기술 목록을 나열하기 위한 것이 아니다. 예를 들어 Phase 3에서 정의한 화면과 Mock JSON은 Phase 4의 FastAPI 응답 계약이 되고, Phase 5의 품질 지표는 이후 대시보드와 모델 학습 조건에 사용된다. Phase 7에서 저장한 모델 평가 결과와 Phase 8의 외부 문서 분석 결과는 최종적으로 같은 리포트 화면에서 제공한다.

현재 이 기록은 Phase 1, 운영 중인 Phase 2, 완료된 Phase 3·5와 Phase 4 핵심 API 연결 결과까지 다룬다. 모델, RAG, AWS 항목은 아직 계획 상태로 구분한다.

## 기술 구성

현재 사용하는 기술과 이후 도입할 기술을 구분했다.

| 영역 | 현재 사용 | 이후 도입 계획 |
| --- | --- | --- |
| Language | Python 3.10, TypeScript | - |
| Data Collection | yfinance | pykrx 등 국내 데이터 소스 비교 |
| Data Processing | pandas | 필요 시 Parquet 기반 처리 |
| Workflow | Apache Airflow 2.10.5 | AWS 연동 Operator |
| Runtime | Docker, Docker Compose | AWS 관리형 실행 환경 검토 |
| Storage | Server 2 SSH 파일 저장소 | Amazon S3 |
| Metadata DB | PostgreSQL 16 | Amazon RDS PostgreSQL |
| ML | scikit-learn | SageMaker, 시계열 딥러닝 실험 |
| API | FastAPI 읽기 전용 조회 계층 | 모델·리포트·Airflow 인증 연동 |
| Desktop | Electron, React, Lightweight Charts | 모델·RAG 결과 연결 |
| AI/RAG | 구조 및 모듈 초안 | 문서 수집, Embedding, Vector Index, AI Report |

## 현재 아키텍처

홈랩은 실행 계층과 데이터 계층을 두 대의 서버로 분리했다.

```text
                         Server 1
                  Compute / Orchestration
                ┌─────────────────────────┐
                │ Docker Compose          │
                │ ├─ Airflow Webserver    │
                │ ├─ Airflow Scheduler    │
                │ └─ Airflow PostgreSQL   │
                │                         │
                │ Python ETL              │
                │ Feature Engineering     │
                └────────────┬────────────┘
                             │
                    SSH      │      PostgreSQL
               file read/write        metadata
                             │
                ┌────────────▼────────────┐
                │        Server 2         │
                │ Data / Persistence      │
                │                         │
                │ File Storage            │
                │ ├─ raw                  │
                │ ├─ processed            │
                │ ├─ curated              │
                │ └─ models               │
                │                         │
                │ PostgreSQL 16           │
                └─────────────────────────┘
```

Server 1은 데이터 수집, 피처 생성, Airflow 스케줄링을 수행한다. Server 2는 파일과 프로젝트 메타데이터를 영속적으로 보관한다. Airflow가 자체적으로 사용하는 PostgreSQL과 ChartMaster 메타데이터 PostgreSQL은 목적이 다르므로 분리했다.

| 저장소 | 위치 | 역할 |
| --- | --- | --- |
| Airflow Metadata DB | Server 1 Docker | DAG Run, Task Instance 등 Airflow 내부 상태 |
| ChartMaster Metadata DB | Server 2 Docker | 자산, 파이프라인 실행, 데이터셋 위치와 행 수 |
| ChartMaster File Storage | Server 2 파일시스템 | OHLCV 원본과 피처 데이터 |

## 데이터 저장 규칙

실제 시계열 데이터는 파일로 저장하고 PostgreSQL에는 파일을 추적하기 위한 메타데이터만 저장한다.

```text
/home/dnhs02/iwantdataengineer/chartmaster/
├── raw/
│   └── market_data/
│       └── provider=yfinance/
│           └── symbol={symbol}/
│               └── data.csv
├── processed/
│   └── features/
│       └── symbol={symbol}/
│           └── data.csv
├── curated/
├── models/
├── reports/
├── logs/
└── backups/
```

경로에 provider와 symbol을 명시해 파일의 출처와 대상을 경로만으로 식별할 수 있게 했다. 이 구조는 AWS 이전 시 다음과 같이 S3 Prefix로 대응할 수 있다.

```text
local  /raw/market_data/provider=yfinance/symbol=005930.KS/data.csv
AWS    s3://<bucket>/raw/market_data/provider=yfinance/symbol=005930.KS/data.csv
```

## Phase 1. 시장 데이터 백필과 저장 계층 구현

### 목표

Phase 1에서는 스케줄러를 도입하기 전에 하나의 Python 명령으로 수집부터 저장, 피처 생성, 메타데이터 기록까지 완료되는 ETL 기준선을 만들었다. 자동화 과정에서 문제가 발생하더라도 ETL 코드와 Airflow 문제를 분리해 진단할 수 있도록 먼저 독립 실행 파이프라인을 구현했다.

### 1. 자산 레지스트리

관리 종목은 `config/assets.json`에서 코드와 분리해 관리한다. 각 자산은 다음 정보를 가진다.

```text
symbol
display_name
market
exchange
asset_type
group
modeling_tier
notes
```

실행 시 `--market`, `--tier`, `--symbols` 옵션으로 대상을 선택한다. `core`와 `experimental` 티어를 나눠 데이터 기간이 충분한 자산과 신규 상장·레버리지 자산을 같은 모델링 기준으로 취급하지 않도록 했다.

### 2. OHLCV 수집과 정규화

`YFinanceMarketDataProvider`가 자산과 날짜 범위를 받아 다음 열을 반환한다.

```text
date, open, high, low, close, adjusted_close, volume
```

수집 결과는 저장 전에 다음 순서로 정규화한다.

1. 필요한 일곱 개 열만 선택한다.
2. `date`를 날짜 타입으로 통일한다.
3. 날짜 오름차순으로 정렬한다.
4. 동일 날짜가 여러 번 존재하면 마지막 행을 유지한다.
5. 인덱스를 다시 생성한다.

이 과정을 신규 수집 데이터뿐 아니라 기존 저장 파일에도 동일하게 적용해 과거 파일의 형식 차이가 병합 결과에 남지 않도록 했다.

### 3. 기존 데이터와 병합

ETL은 기본적으로 파일을 매번 교체하지 않는다. 기존 raw CSV를 먼저 읽고 신규 수집 결과와 합친 다음 날짜를 기준으로 다시 정렬하고 중복을 제거한다.

```text
existing raw CSV
       +
newly fetched rows
       │
       ▼
concat -> sort by date -> deduplicate -> overwrite merged CSV
```

따라서 같은 날짜 범위를 다시 실행해도 동일 날짜의 행이 계속 늘어나지 않는다. 필요할 때만 `--replace-existing` 옵션으로 기존 이력을 교체할 수 있다.

### 4. SSH 기반 파일 저장소

Server 1의 ETL 프로세스는 Server 2의 파일 저장소를 SSH로 읽고 쓴다. 저장소 구현은 `ObjectStorage` 인터페이스 뒤에 숨겨 로컬 디버깅과 Server 2 저장을 같은 ETL 코드에서 사용할 수 있게 했다.

| 구현체 | 사용 상황 |
| --- | --- |
| `LocalObjectStorage` | 격리된 로컬 테스트와 디버깅 |
| `SshObjectStorage` | 홈랩 Server 2에 실제 데이터 저장 |

SSH 저장은 Batch Mode와 전용 키를 사용하며, 원격 디렉터리를 생성한 뒤 표준 입력으로 파일 내용을 전달한다. 읽을 때는 원격 파일을 가져와 pandas DataFrame으로 복원한다.

이 추상화를 통해 이후 `S3ObjectStorage`를 추가하더라도 ETL의 수집·피처 생성 로직은 유지할 수 있다.

### 5. 피처 생성

raw OHLCV에서 다음 피처를 생성한다.

| 피처 | 계산 방식 |
| --- | --- |
| `turnover_value` | `close × volume` |
| `return_1d` | 1거래일 수익률 |
| `return_5d` | 5거래일 수익률 |
| `return_20d` | 20거래일 수익률 |
| `volume_change_1d` | 거래량 1일 변화율 |
| `moving_average_5` | 종가 5일 이동평균 |
| `moving_average_20` | 종가 20일 이동평균 |
| `volatility_5` | 1일 수익률의 5일 이동 표준편차 |
| `volatility_20` | 1일 수익률의 20일 이동 표준편차 |

초기 분류 모델을 위한 타깃도 함께 생성한다.

```text
future_5d_return = close(t+5) / close(t) - 1
target_positive_5d_return = future_5d_return > 0
```

마지막 5개 행처럼 미래 가격이 아직 존재하지 않는 구간은 타깃을 결측값으로 유지한다. 모델 학습 시 이 행을 제외함으로써 미래 정보가 없는 데이터를 임의로 음성 클래스로 처리하지 않는다.

### 6. PostgreSQL 메타데이터 기록

ETL 시작 시 `pipeline_runs`에 `running` 상태를 기록하고, 처리 완료 후 `success`, `partial_success`, `failed` 중 하나로 갱신한다.

```text
pipeline start
  -> pipeline_runs: running
  -> asset registry upsert
  -> asset별 raw 저장
  -> asset별 processed 저장
  -> datasets metadata 기록
  -> pipeline_runs 상태 갱신
```

현재 구현된 테이블은 다음과 같다.

| 테이블 | 구현한 역할 |
| --- | --- |
| `assets` | 심볼, 시장, 거래소, 자산 유형, 모델링 티어 관리 |
| `pipeline_runs` | 파이프라인명, 시작·종료 시각, 상태, 메시지 기록 |
| `datasets` | 데이터 유형, provider, symbol, URI, 행 수, 날짜 범위 기록 |
| `model_versions` | 모델명, 버전, artifact URI, 학습·검증 행 수 기록 |
| `model_metrics` | 모델 버전별 평가 지표 기록 |

`model_versions`와 `model_metrics`의 스키마와 저장 코드는 준비했지만, 현재 자동 수집 운영 범위에서는 아직 레코드가 생성되지 않았다.

### 7. 종목별 실패 격리

한 종목의 수집 실패가 전체 자산 처리를 즉시 중단하지 않도록 종목별 예외를 수집한다. 일부 종목만 실패하면 정상 종목의 결과는 저장하고 전체 실행 상태를 `partial_success`로 남긴다. 장애 분석이나 엄격한 검증이 필요할 때는 `--fail-fast`로 첫 실패에서 중단할 수 있다.

### Phase 1 실행 결과

확인일 기준 실제 저장 및 메타데이터 상태는 다음과 같다.

| 지표 | 결과 |
| --- | ---: |
| 등록 자산 | 29개 |
| Raw 파일 영역 | 약 21 MB |
| Processed 피처 영역 | 약 64 MB |
| `assets` | 29 rows |
| `pipeline_runs` | 34 rows |
| 성공한 Pipeline Run | 34건 |
| `datasets` | 712 rows |

## Phase 2. Airflow 자동화 구현

### 목표

Phase 2에서는 Phase 1의 독립 실행 ETL을 변경하지 않고 Airflow가 정해진 날짜 범위와 시장을 전달하도록 구성했다. 한국장과 미국장의 시간대를 분리하고, 홈서버가 꺼져 있던 기간과 데이터 제공자의 과거 값 정정을 함께 처리하는 것이 목표였다.

### 1. Docker Compose 실행 환경

Airflow는 Server 1에서 세 개의 상시 컨테이너로 실행한다.

| 서비스 | 역할 |
| --- | --- |
| `airflow-webserver` | Airflow UI와 상태 확인 |
| `airflow-scheduler` | DAG 스케줄 계산과 Task 실행 |
| `airflow-postgres` | Airflow 내부 메타데이터 저장 |

초기화 전용 `airflow-init` 서비스는 DB Migration과 관리자 계정 생성을 수행한 뒤 종료한다. Webserver와 Scheduler는 초기화 완료와 PostgreSQL Health Check 통과 후 시작한다.

주요 설정은 다음과 같다.

| 항목 | 설정 |
| --- | --- |
| Airflow | 2.10.5, Python 3.10 |
| Executor | LocalExecutor |
| 기본 시간대 | Asia/Seoul |
| 예제 DAG | 비활성화 |
| 새 DAG 기본 Pause | 비활성화 |
| 재시작 정책 | `unless-stopped` |
| Web UI | 호스트 8081 → 컨테이너 8080 |

프로젝트 소스, DAG, 로그, 환경 설정과 SSH 키를 볼륨으로 연결한다. 서버가 재부팅되면 systemd가 Docker를 시작하고, `unless-stopped` 정책에 따라 Airflow 컨테이너가 다시 실행된다.

### 2. 시장별 DAG 분리

현재 운영하는 DAG는 두 개다.

| DAG | Schedule | Timezone | Task |
| --- | --- | --- | --- |
| `daily_kr_market_data_etl` | 평일 16:10 | Asia/Seoul | `collect_kr_daily_ohlcv` |
| `daily_us_market_data_etl` | 평일 17:30 | America/New_York | `collect_us_daily_ohlcv` |

한국과 미국의 장 마감 시각 및 일광절약시간 차이를 코드에서 임의 계산하지 않고 DAG Timezone으로 표현했다. 각 DAG는 `BashOperator`로 Phase 1 ETL을 호출하며 `--market KR` 또는 `--market US`만 다르게 전달한다.

### 3. Catchup으로 누락 실행 복구

두 DAG 모두 `catchup=True`다. 홈서버가 스케줄 시점에 꺼져 있더라도 Scheduler가 다시 실행되면 미처리 Data Interval에 대한 DAG Run을 생성한다.

동시에 `max_active_runs=1`로 제한해 여러 과거 실행이 생성되더라도 같은 DAG의 Run이 Server 1에서 한꺼번에 실행되지 않도록 했다. 이는 CPU 2코어, 메모리 약 8 GB인 홈서버의 자원 경합을 줄이기 위한 설정이다.

### 4. 10일 Overlap 수집

각 DAG Run은 논리적 실행일 하루만 요청하지 않고 Data Interval 종료일을 기준으로 최근 10일을 다시 수집한다.

```text
start = market timezone 기준 data_interval_end - 10일
end   = market timezone 기준 data_interval_end + 1일
```

가져온 데이터는 Phase 1의 merge/dedup 로직을 통과한다. 따라서 최근 날짜를 반복 수집해도 중복 행이 증가하지 않으며, 데이터 제공자가 과거 값을 수정하거나 늦게 제공한 경우 기존 행을 최신 값으로 교체할 수 있다.

```text
Airflow catchup       = 실행되지 않은 날짜의 Run 복구
10-day overlap        = 최근 데이터의 누락·정정 흡수
date merge/dedup      = 반복 실행에 따른 중복 방지
```

세 기능은 목적이 다르며 함께 사용해야 홈서버 중단과 제공자 데이터 정정을 모두 처리할 수 있다.

### 5. 재시도와 동시 실행 제어

Task 실패 시 최대 3회 재시도하고 재시도 사이에 20분을 둔다. 일시적인 네트워크 단절이나 데이터 제공자 오류가 즉시 영구 실패로 끝나지 않게 하기 위한 설정이다.

| 항목 | 값 |
| --- | --- |
| `retries` | 3 |
| `retry_delay` | 20분 |
| `depends_on_past` | false |
| `max_active_runs` | 1 |

`depends_on_past=False`이므로 이전 날짜의 실패가 이후 모든 실행을 막지는 않는다. 개별 실행의 실패는 Airflow 로그와 ChartMaster의 `pipeline_runs`에서 각각 오케스트레이션 관점과 ETL 관점으로 확인할 수 있다.

### 6. 컨테이너와 원격 저장소 연결

Airflow 컨테이너는 Server 2 접근 설정을 읽기 전용 환경 파일로 전달받고 SSH 공개키 인증으로 파일을 저장한다. 프로젝트 메타데이터는 Server 2의 PostgreSQL 5432 포트로 기록한다.

즉, Task 하나가 실행되면 다음 경계를 통과한다.

```text
Airflow Scheduler container
  -> Python ETL process
  -> yfinance market data
  -> SSH -> Server 2 file storage
  -> PostgreSQL -> Server 2 metadata DB
```

### Phase 2 운영 상태

확인일 기준 다음 상태로 운영 중이다.

| 항목 | 상태 |
| --- | --- |
| Airflow Webserver | Healthy |
| Airflow Scheduler | Running |
| Airflow Metadata PostgreSQL | Healthy |
| 한국장 DAG | 운영 중 |
| 미국장 DAG | 운영 중 |
| 컨테이너 자동 재시작 | 적용 |
| ETL Pipeline Run | 34건 모두 success |

Phase 2는 구현을 마쳤지만 운영 검증은 계속 진행 중이다. 네트워크 단절, Server 2 중단, 강제 Task 실패와 같은 상황에서 재시도와 복구 절차를 의도적으로 시험하는 작업은 별도 과제로 남아 있다.

## Phase 5. 데이터 품질과 Curated 계층 구현

### 목표와 현재 상태

데이터가 매일 저장된다는 사실만으로 모델 학습에 사용할 수 있다고 볼 수 없다. Phase 5에서는 같은 검사를 반복 실행할 수 있게 코드화하고, 원천 공급자의 오류를 raw에서 지우지 않으면서 모델 입력용 기준 데이터를 만드는 것을 목표로 했다.

Phase 5는 완료했다. 품질 검사, 거래소 캘린더, pykrx_naver 보조 수집, curated 생성, 재처리와 Airflow Task 연결을 구현했고, 최신 서버2 데이터 기준으로 29개 종목 전체가 품질 검사를 통과했다. 독립 KRX 원시 시세는 계정 인증이 필요하므로 Phase 5의 완료 조건에서 분리하고 후속 보강 항목으로 남겼다.

### 1. 첫 품질 검사에서 발견한 문제

29개 종목의 raw와 processed 파일을 검사했을 때 날짜 중복과 일반 OHLCV 결측은 없었지만 다음 문제가 발견됐다.

| 문제 | 최초 결과 | 의미 |
| --- | ---: | --- |
| SK하이닉스 `adjusted_close <= 0` | 778행 | 2000-01-04~2002-12-26 보정주가 사용 불가 |
| 한국 종목 OHLC 관계 모순 | 16행 | 종가가 같은 행의 고가·저가 범위를 벗어남 |
| 7일 초과 날짜 공백 | 종목별 2구간 | 실제 휴장과 누락을 구분하지 못하는 규칙 |
| 무한대 피처 | 다수 | 전일 거래량이 0일 때 `volume_change_1d`가 무한대가 됨 |

무한대 피처는 계산식에서 양·음의 무한대를 결측으로 바꾸고 processed 파일 29개를 재처리했다. raw는 변경하지 않았다.

### 2. 달력 일수 대신 거래소 세션 사용

처음에는 날짜 간격이 7일을 넘으면 경고했다. 이 방식은 장기 휴장도 누락으로 판단하는 문제가 있었다.

```text
2017-09-29 -> 2017-10-10: 11일
2025-10-02 -> 2025-10-10: 8일
```

XKRX 거래 캘린더로 확인한 결과 두 구간 모두 중간에 예정 거래 세션이 없는 실제 휴장이었다. 따라서 단순 날짜 차이 검사를 제거하고 한국장은 XKRX, 미국장은 XNYS의 예정 세션과 실제 날짜 집합을 비교하도록 변경했다.

캘린더도 완전한 정답은 아니었다. XKRX 라이브러리에 아직 반영되지 않은 `2026-06-03`, `2026-07-17` 휴장일이 예정 세션으로 나타나 프로젝트 예외 목록으로 관리했다. 반대로 실제 거래일인데 Yahoo 데이터에 없던 날짜도 찾았다.

XNYS도 1960년대 휴일 일부를 거래 세션으로 반환해 장기 미국 종목에서 68개의 오탐이 발생했다. 미국 세션 누락 검사는 캘린더 신뢰 구간인 1970년 이후로 제한하고, 가격·거래량·중복 같은 구조 검사는 1962년부터의 전체 데이터에 계속 적용했다.

| 구분 | 날짜 |
| --- | --- |
| pykrx_naver로 확인하고 보완 | 2017-09-22, 2017-12-20, 2022-01-03, 2022-05-09, 2025-09-19 |
| 확인된 임시공휴일로 캘린더 예외 처리 | 2007-03-02 |
| 실제 휴장으로 판정 | 2017-09-30~10-09, 2025-10-03~10-09, 2026-06-03, 2026-07-17 |

### 3. 공급자 교차 검증

pykrx의 공개 API를 확인하면서 출처를 다시 구분했다. `adjusted=False`는 KRX 원시 시세를 요청하지만 현재 버전에서는 `KRX_ID`, `KRX_PW` 인증이 필요했다. `adjusted=True`는 Naver 기반 수정주가 경로이며 인증 없이 조회할 수 있었다.

따라서 이를 KRX 원천이라고 부르지 않고 `pykrx_naver`라는 보조 공급자로 명시했다. Yahoo에서 OHLC가 모순이었던 16개 날짜는 pykrx_naver에서 모두 정상적인 OHLCV 행을 확인했다. 예를 들어 삼성전자 `2024-10-14`는 다음과 같았다.

```text
Yahoo          open=59,500 high=61,200 low=59,400 close=59,300
pykrx_naver    open=59,500 high=61,200 low=59,400 close=60,800
```

Yahoo 값은 종가가 저가보다 낮아 일봉 관계를 위반하지만 보조 공급자 값은 정상 범위에 있다.

### 4. Raw를 보존하고 Curated에서 해결

원천값을 직접 수정하면 나중에 어떤 값이 공급자 응답이고 어떤 값이 프로젝트 교정값인지 구분할 수 없다. 저장 흐름을 다음처럼 확장했다.

```text
raw/provider=yfinance
raw/provider=pykrx_naver
          │
          ▼
공급자 비교 및 품질 판정
          │
          ▼
curated/market_data
          │
          ▼
processed/features
```

- Yahoo raw는 변경하지 않는다.
- 보조 공급자 응답도 별도 raw 경로에 저장한다.
- OHLC 모순 16행은 curated에서 전체 OHLCV 행을 교체한다.
- Yahoo에 없던 거래일 5개는 curated에 추가한다.
- SK하이닉스의 잘못된 보정주가는 curated에서 `NaN`으로 표시한다.
- 각 curated 행에는 `source_provider`, `quality_status`를 남긴다.
- 피처는 한국장 curated 데이터를 기준으로 다시 생성한다.

PostgreSQL에는 `data_quality_issues` 테이블을 추가했다. 종목, 관찰일, 공급자, 문제 코드, 심각도, 상태와 해결 방법을 기록한다. OHLC 교체와 5개 거래일 보완은 `resolved`, SK하이닉스 보정주가는 `open` 상태다. 이후 `2007-03-02`는 임시공휴일로 확인되어 캘린더 예외에 반영했고 누락 경고에서 제외했다.

### 5. 재처리와 멱등성

백필과 재처리는 분리했다. 백필은 공급자에서 다시 수집해 raw에 날짜 기준으로 병합하고, 재처리는 저장된 raw를 읽어 processed만 다시 만든다. 재처리 명령은 기본이 dry-run이며 `--write`를 명시해야 저장한다.

curated 파이프라인도 이미 저장된 pykrx_naver 데이터를 먼저 확인한다. 필요한 날짜가 있으면 기존 보조 원천과 병합하고, 같은 작업을 다시 실행해도 날짜 중복이 늘어나지 않는다.

### 6. 구현 중 발생한 실패

첫 실제 curated 실행에서 12종목의 파일 생성은 성공했지만 품질 이력 저장이 실패했다. psycopg3 `Connection` 객체에 `executemany`를 직접 호출한 것이 원인이었다.

```text
'Connection' object has no attribute 'executemany'
```

cursor를 생성해 `cursor.executemany()`를 호출하도록 수정했다. 같은 파이프라인을 다시 실행해 파일 중복 없이 12종목 모두 성공했고 PostgreSQL 이력도 정상 저장됐다. 기존 모델 지표 저장 코드에도 같은 문제가 있어 함께 수정했다.

### 7. Airflow 품질 Gate

한국장 DAG는 다음 세 Task를 순서대로 실행하도록 확장했다.

```text
collect_kr_daily_ohlcv
  -> curate_kr_market_data
  -> validate_kr_market_data
```

미국장은 아직 원천 이상이 발견되지 않아 `수집 -> 품질 검사` 구조를 유지한다. 품질 오류가 하나라도 있으면 Task가 종료 코드 1을 반환하고, 공급자 한계나 미해결 교차 검증 항목은 경고 리포트로 남긴다.

### Phase 5 최종 결과

| 항목 | 현재 결과 |
| --- | --- |
| 품질 단위 테스트 | 11개 통과 |
| 전체 테스트 | 14개 통과 |
| 한국 종목 Curated 생성 | 12개 성공 |
| OHLC 이상 교체 | 16행 |
| 누락 거래일 보완 | 종목별 5행 |
| 중복 날짜 | 0 |
| 품질 오류 | 0 |
| 전체 품질 검사 | 29종목 PASS, 오류 0, 경고 1 |
| 미국장 전체 품질 검사 | 17종목, 오류·경고 0 |
| Airflow 한국장 수동 DAG | 수집·curated·검사 3 Task 모두 success |
| Airflow 한국장 정기 DAG | 최근 정기 실행 success |
| Airflow 미국장 정기 DAG | 최근 정기 실행 success |
| 미해결 | SK하이닉스 보정주가 778행 |

품질 검사에 거래소 세션을 처음 적용했을 때 미국장 전체 검사가 4분 30초 걸렸다. 프로파일링 결과 세션마다 pandas Series의 최소·최대 날짜를 다시 계산해 수만 번의 전체 축소 연산이 발생하고 있었다. 최소·최대 날짜를 한 번 계산해 재사용한 뒤 같은 검사가 13.7초로 줄었다.

최신 품질 리포트는 서버2의 `reports/data_quality/market=ALL/latest.json`에 저장했다. 품질 오류는 0이고, 경고 1건은 모델 학습을 막는 구조 오류가 아니라 공급자 한계 또는 추가 확인이 필요한 항목으로 분리했다.

Phase 5는 여기서 완료 처리한다. 다만 KRX 계정 인증 기반 원시 시세 검증, 네트워크 단절·DB 중단 같은 장애 주입 테스트, 백업/복구 훈련은 Phase 6 운영 안정성 작업으로 넘긴다.

## 구현 과정에서 해결한 문제

### Airflow DB와 프로젝트 DB의 역할 충돌

처음에는 PostgreSQL을 하나의 DB로 설명하기 쉬웠지만, 실제로는 Airflow 내부 상태와 프로젝트 데이터 카탈로그의 수명주기와 책임이 다르다. 두 DB를 분리해 Airflow를 재구성하더라도 Server 2의 데이터셋 메타데이터가 영향을 받지 않게 했다.

### 홈서버가 항상 켜져 있지 않은 문제

일반적인 상시 서버를 전제로 한 단순 Cron 스케줄은 전원이 꺼져 있던 실행을 복구하지 않는다. Airflow Catchup으로 논리적 실행일을 복구하고, Overlap 수집으로 실제 시장 데이터 누락을 다시 확인하도록 구성했다.

### 재실행 시 중복 데이터가 생기는 문제

파일에 단순 Append하면 Catchup과 Overlap 실행 횟수만큼 같은 날짜가 중복될 수 있다. 기존 파일과 신규 데이터를 합친 후 날짜 기준으로 마지막 행만 유지해 반복 실행 가능한 형태로 바꿨다.

### 한 종목의 장애가 전체 수집을 막는 문제

신규 상장 또는 데이터 제공 문제로 일부 심볼이 실패할 수 있다. 종목별 실패를 격리하고 정상 결과를 보존하며, 실행 상태를 `partial_success`로 구분하도록 구현했다.

## Phase 3. Electron Dashboard와 실데이터 조회 화면

Phase 5를 진행하면서 품질 검사와 모델링은 데이터에 따라 계속 수정될 수 있지만, 사용자가 어떤 정보를 어떤 흐름으로 볼지는 이후 API와 모델 출력 계약 전체에 영향을 준다는 점을 확인했다. 따라서 Phase 5를 폐기한 것이 아니라 잠시 분기해 Electron 화면 구조를 먼저 구현했다.

Electron은 React와 TypeScript로 구성하고 금융 시계열은 Lightweight Charts를 사용했다. 첫 구현은 Mock Provider로 시작했지만 UI가 저장소 구조를 알지 않도록 `DashboardDataProvider` 계약을 두고 Mock과 Live API 구현을 분리했다.

```text
Electron / React
  -> DashboardDataProvider
       -> Mock Provider
       -> Live API Provider
            -> Server 1 FastAPI
                 -> SSH read
                      -> Server 2 processed/features, reports
```

구현한 화면은 Dashboard, 종목 목록, 종목 상세, 데이터 상태, 데이터 검증, 이벤트, 예측, 파이프라인, 리포트다. 아직 모델과 RAG 결과가 없으므로 예측 확률이나 원인 분석을 임의로 생성하지 않고 `model_not_ready`, `not_analyzed`, `planned` 상태로 표시한다.

종목 상세 차트는 전체 이력을 한 번 읽고 `ALL / 5Y / 1Y / 6M / 1M / 5D` 버튼으로 보이는 구간만 바꾼다. 기간별 데이터만 요청했을 때 과거로 이동하면 빈 공간이 나타났던 문제를 해결하기 위해 전체 시계열을 유지한 채 visible range만 조절했다. 날짜별 OHLCV hover, 이동평균, 거래량, drag 탐색과 확대 화면도 추가했다.

데이터 검증 화면은 시장별 요약뿐 아니라 종목, 심각도, 검사 코드, 설명, 영향 행 수와 검사 기준일을 표시한다. 현재 실제 리포트에서는 오류 0건, 경고 1건, 영향 종목 1개를 조회하며, 남은 경고는 SK하이닉스의 수정주가 이상 778행이다. 한국장 `2007-03-02`는 임시공휴일로 확인되어 캘린더 예외에 반영했다.

Phase 4 전체를 완료한 것은 아니다. 다만 Electron이 서버2에 직접 접근하지 않도록 서버1에 읽기 전용 FastAPI를 두고 다음 핵심 엔드포인트를 구현했다.

```text
GET /health
GET /api/v1/dashboard
GET /api/v1/assets/{symbol}/prices?range=ALL|5Y|1Y|6M|1M|5D
```

API 컨테이너는 Airflow와 별도 이미지로 분리하고 `restart: unless-stopped`와 healthcheck를 설정했다. 컨테이너를 UID 1000으로 실행하면서 이미지에 해당 사용자가 없어 OpenSSH가 `No user exists for uid 1000`으로 실패한 문제도 확인했다. API 이미지에 실행 사용자를 명시적으로 만들고 서버2 SSH 키를 읽기 전용으로 마운트해 해결했다.

Phase 3의 상세 구현과 화면별 설명은 별도 글 `04-phase3-electron-dashboard.md`에 정리한다.

## 현재 한계

- pykrx_naver는 보조 공급자이며 KRX 인증 기반 원시 시세 검증은 후속 보강 항목이다.
- CSV 기반 저장은 현재 데이터 규모에서는 충분하지만 파일 수와 조회 패턴이 커지면 Parquet 전환을 검토해야 한다.
- Airflow 컨테이너에 호스트 SSH 디렉터리 전체가 마운트되어 있어 서비스 전용 키만 전달하도록 범위를 줄여야 한다.
- Server 2의 DB 포트 접근 대상을 방화벽으로 더 엄격하게 제한해야 한다.
- 자동 백업은 디렉터리 설계 수준이며 실제 복원 훈련이 필요하다.
- 강제 실패, 네트워크 단절, DB 중단 상황의 재시도·복구 검증은 Phase 6에서 다룬다.
- 파일 저장소와 PostgreSQL을 함께 검증하는 자동 통합 테스트는 아직 부족하다.
- 모델 테이블과 저장 코드는 준비돼 있지만 모델 학습 자동화는 아직 구현하지 않았다.
- 모델 학습, RAG, AI 리포트와 AWS 이전은 아직 계획 단계다.
- FastAPI는 가격·품질 조회 중심이며 Airflow REST 인증과 모델·리포트 API는 남아 있다.

## 요약

ChartMaster에서 현재 구현한 핵심은 예측 모델이 아니라 반복 실행 가능한 시장 데이터 파이프라인이다.

```text
yfinance OHLCV 수집
  -> 기존 이력과 날짜 기준 병합
  -> 중복 제거
  -> Server 2 raw 저장
  -> 거래소 세션 기반 누락 검사
  -> 보조 공급자 교차 검증
  -> Server 2 curated 저장
  -> curated 기반 피처 생성
  -> Server 2 processed 저장
  -> PostgreSQL 실행·데이터셋 메타데이터 기록
  -> Airflow 시장별 스케줄 및 실패 재시도
```

Phase 1에서는 독립 실행 가능한 ETL과 저장 계층을 구현했고, Phase 2에서는 이를 Airflow로 자동화했다. Phase 3에서는 Electron의 정보 구조와 실제 데이터 조회 화면을 완성했고, Phase 4의 핵심 FastAPI 경계를 함께 검증했다. Phase 5에서는 실제 공급자 이상, 원천 보존, 교차 검증, curated 계층과 품질 Gate를 닫았다. 다음은 Phase 6에서 백업, 복구, 장애 대응을 운영 절차로 정리하는 단계다.

## 참고 자료

- [pykrx OHLCV 공개 API 구현](https://github.com/sharebook-kr/pykrx/blob/master/pykrx/stock/stock_api.py)
- [exchange_calendars의 XKRX 캘린더 등록](https://github.com/gerrymanoim/exchange_calendars/blob/master/exchange_calendars/calendar_utils.py)
- [한국거래소 Market Closing 안내](https://global.krx.co.kr/contents/GLB/05/0501/0501110000/GLB0501110000.jsp)

---

마지막 확인일: 2026-08-22
