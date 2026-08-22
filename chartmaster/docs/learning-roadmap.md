# ChartMaster 학습 로드맵

이 문서는 ChartMaster의 최신 Phase 계획을 정리한다.

프로젝트의 목적은 완성된 투자 서비스를 빠르게 만드는 것이 아니라, 데이터 엔지니어링과 인프라 엔지니어링 관점에서 시장 데이터 플랫폼을 직접 설계하고 운영해보는 것이다.

## 진행 원칙

- 이미 진행한 Phase 1~3의 흐름은 유지한다.
- 로컬 서버 환경에서 데이터 수집, 저장, 자동화, 검증 흐름을 먼저 충분히 익힌다.
- 서버2는 AWS S3/RDS로 넘어가기 전의 학습용 데이터 서버로 사용한다.
- 리눅스 사용자, 권한, 내부망, SSH 같은 서버 기초 구조는 별도 인프라 프로젝트에서 자세히 다룬다.
- 이 프로젝트에서는 그 서버 환경 위에서 데이터 플랫폼의 서비스 경계, 저장소 분리, 자동화, 백업/복구, 운영 관찰성을 어떻게 설계하는지에 집중한다.
- 데이터 분석과 모델링은 데이터가 충분히 쌓이고 품질을 확인한 뒤 본격화한다.
- 화면 구조와 API 계약은 한 번 정하면 크게 바뀌기 어렵기 때문에 Electron Dashboard와 FastAPI 계약을 먼저 설계한다.
- AWS는 로컬 구조가 안정된 뒤 S3, RDS, SageMaker, CloudWatch 순서로 확장한다.

## 현재 위치

```text
Phase 1: 완료
  과거 OHLCV 백필, 서버2 파일 저장소, PostgreSQL metadata, 기본 피처 생성

Phase 2: 운영 중
  Airflow 기반 한국장/미국장 일봉 자동 수집, catchup, overlap merge, dedup
  실패/retry 강제 테스트는 별도 운영 검증 단계로 남김

Phase 3: 완료
  Electron Dashboard 정보 구조, 종목별 대화형 차트, Mock/Live Provider 계약 구현
  데이터 상태·검증·이벤트·예측·파이프라인·리포트 화면 구성

Phase 4: 핵심 연결 구현
  서버1 FastAPI와 서버2 SSH 파일 저장소 연결
  Electron에서 29개 종목의 실데이터와 품질 이슈 조회
  Airflow 실행 상태 인증 연동과 향후 모델·리포트 API는 후속 확장

Phase 5: 완료
  품질 검사, 거래소 캘린더, 백필, curated 교차 검증, 피처 재처리 구현
  최신 품질 검사 29종목 PASS, 오류 0, 경고 1
  KRX 인증 기반 독립 원천 검증은 후속 보강 항목으로 분리

Phase 6: 진행 중
  운영 정상 상태 기준, 파일 저장소 백업, PostgreSQL dump/restore 1차 검증 완료
  낮은 위험 장애 실험부터 순차 진행 예정
```

## Phase 1: 로컬 시장 데이터 기준선과 서버2 저장 구조

목표:

- 초기 자산 목록의 과거 OHLCV 데이터를 수집한다.
- 서버2에 ChartMaster 전용 파일 저장소를 만든다.
- raw, processed, curated, models, reports, logs, backups 영역을 분리한다.
- 가격, 거래량, 거래대금, 변동성, 모멘텀 기반 기본 피처를 만든다.
- 서버2 PostgreSQL에 실행 이력과 데이터셋 메타데이터를 저장한다.

산출물:

- 서버2 파일 저장소 구조
- raw 시장 데이터 CSV
- processed feature CSV
- PostgreSQL `pipeline_runs`, `datasets` metadata
- 수동 실행 가능한 Python ETL

학습 포인트:

- `yfinance` 사용법
- OHLCV 데이터 구조
- raw 데이터와 processed 데이터 분리
- 파일 저장소와 DB 역할 분리
- metadata DB 설계
- 로컬 환경에서 S3/RDS 역할 이해

## Phase 2: Airflow 로컬 자동화

목표:

- `daily_kr_market_data_etl` DAG를 만든다.
- `daily_us_market_data_etl` DAG를 만든다.
- 한국장과 미국장 장마감 시간을 분리해서 스케줄링한다.
- 서버가 켜져 있으면 정해진 시간에 자동 수집한다.
- 서버가 꺼져 있던 동안 놓친 실행은 Airflow catchup으로 복구한다.
- 10일 overlap 수집과 날짜 기준 merge/dedup으로 누락과 데이터 정정을 흡수한다.

산출물:

- Airflow Docker Compose 실행 환경
- 한국장/미국장 분리 DAG
- Airflow Web UI
- 서버 재시작 후 자동 실행 구조
- 수집 성공/실패/실행 시간 확인 흐름

학습 포인트:

- Airflow DAG
- Task 의존성
- schedule interval
- catchup
- retry
- Docker Compose 운영
- Airflow metadata DB와 프로젝트 metadata DB의 차이

## Phase 3: Electron Dashboard UI 설계와 Mock Prototype

목표:

- 실제 모델, RAG, 리포트가 완성되기 전에 먼저 앱 화면 구조를 설계한다.
- 로컬 PC에서 Electron 데스크톱 앱을 개발한다.
- Dashboard, Assets, Asset Detail, Events, Airflow/Pipelines 화면을 우선 구현한다.
- Predictions, Reports, Settings 화면은 mock 또는 placeholder로 둔다.
- mock JSON을 이용해 화면 상태와 데이터 표시 방식을 검증한다.
- 나중에 FastAPI가 반환할 응답 형태를 mock data shape으로 먼저 고정한다.

산출물:

- Electron 프로젝트 기본 구조
- dark/neon 금융 대시보드 스타일
- mock/live data provider
- 종목 목록 화면
- 전체 기간과 `5Y / 1Y / 6M / 1M / 5D` 구간을 탐색하는 종목 상세 차트
- 날짜별 OHLCV hover와 과거 구간 drag 탐색
- 종목별 품질 이슈 상세 화면
- 급등/급락 이벤트 화면
- Airflow/Pipelines 상태 화면
- 모델 미준비 상태와 향후 예측선 계약

학습 포인트:

- Electron 데스크톱 앱 구조
- 화면 정보 구조 설계
- mock data 기반 UI 개발
- 차트/테이블/상태 뷰 구성
- 운영 시스템 상태를 사용자 화면에 표현하는 방식
- 화면 요구사항에서 API 계약을 역설계하기

## Phase 4: FastAPI 데이터 제공 계층과 서비스 경계 설계

목표:

- Electron 앱이 직접 서버2 파일 저장소나 PostgreSQL에 접근하지 않도록 FastAPI 계층을 둔다.
- Phase 3의 mock JSON과 동일한 형태의 API response contract를 정의한다.
- mock provider와 live provider를 분리한다.
- 서버1 API 계층과 서버2 데이터 저장소의 연결 지점을 명확히 한다.
- 환경변수, 접속 정보, API URL, Airflow UI URL 같은 설정 값을 코드와 분리한다.

산출물:

- FastAPI 프로젝트 구조
- API response schema
- mock provider
- live provider로 교체 가능한 interface
- Electron과 API 연결 설정
- 서비스 경계 문서

학습 포인트:

- FastAPI
- API contract
- mock provider와 live provider 분리
- Electron과 backend 연결
- 클라이언트가 DB에 직접 붙지 않아야 하는 이유
- 서비스 경계와 설정 관리

## Phase 5: 데이터 품질, 백필, 재처리 전략

목표:

- 국내장과 미국장 종목 수를 늘린 결과를 검증한다.
- yfinance, pykrx, Stooq 등 데이터 소스별 커버리지와 한계를 비교한다.
- 누락 데이터, 중복 데이터, 날짜 범위, row count 차이를 점검한다.
- 백필을 다시 실행해야 하는 상황과 절차를 정리한다.
- 수집 실패나 데이터 정정이 발생했을 때 재처리하는 전략을 만든다.

산출물:

- 종목 유니버스 기준 문서
- 데이터 소스 coverage 비교표
- 데이터 품질 체크 스크립트
- 백필 재실행 runbook
- 재처리 기준 문서
- 신규 종목 추가 절차

학습 포인트:

- 자산 유니버스 설계
- 데이터 소스 검증
- coverage gap
- 백필 전략
- idempotent ETL
- 재처리와 중복 방지
- rate limit과 실패 처리

## Phase 6: 운영 안정성과 백업/복구 설계

목표:

- 서버2 raw/processed 데이터 백업 전략을 만든다.
- PostgreSQL metadata DB의 backup/restore 절차를 정리한다.
- Airflow DAG 실패, 재시도, 수동 재실행 절차를 문서화한다.
- 컨테이너 재시작, 서버 재부팅, 네트워크 일시 장애 상황에서 확인할 항목을 정리한다.
- 운영 로그와 상태 점검 체크리스트를 만든다.

산출물:

- 파일 저장소 백업 정책
- PostgreSQL backup/restore runbook
- Airflow 장애 대응 runbook
- 운영 점검 체크리스트
- 로그 확인 절차
- 복구 테스트 기록

현재 진행:

- Server 1/Server 2 정상 상태 기준을 문서화했다.
- Server 2 파일 저장소 tar 백업을 생성하고 목록을 확인했다.
- Server 2 PostgreSQL metadata dump를 생성했다.
- 운영 DB를 덮어쓰지 않고 임시 DB에 restore한 뒤 삭제하는 복구 테스트를 완료했다.
- 장애 실험은 FastAPI 컨테이너 재시작부터 낮은 위험 순서로 진행한다.

학습 포인트:

- backup과 restore 차이
- metadata DB 백업
- object/file storage 백업
- 장애 대응 runbook
- 운영 로그 확인
- 재시작 후 자동 복구 검증
- 데이터 플랫폼 운영 안정성

## Phase 7: 머신러닝 모델 학습 파이프라인

목표:

- processed feature 데이터를 이용해 첫 baseline 모델을 학습한다.
- 다음 날 수익률, 5거래일 뒤 상승 여부, 변동성 확대 여부 등 문제 정의를 비교한다.
- naive baseline과 비교한다.
- 모델 artifact와 평가 metric을 서버2에 저장한다.
- PostgreSQL에는 모델 버전, metric, 산출물 위치를 기록한다.
- 이후 Airflow 기반 재학습으로 확장할 수 있게 구조를 잡는다.

산출물:

- baseline model training script
- train/validation/test split 기준
- model artifact 저장 구조
- model metadata table
- metric 기록
- 재학습 DAG 초안

학습 포인트:

- 기본 피처 엔지니어링
- time series split
- backtesting leakage 방지
- Accuracy, Precision, Recall, F1-score
- 회귀 metric과 분류 metric 차이
- 모델 artifact와 metadata 관리
- 모델 학습 파이프라인의 재현성

## Phase 8: RAG와 외부 요인 분석 계층

목표:

- 뉴스, 리포트, 매크로 이벤트 문서를 수집한다.
- 외부 문서는 시장 데이터와 별도로 raw 영역에 저장한다.
- 검색 연습을 위한 간단한 vector index를 만든다.
- RAG 기반 외부 요인 요약을 생성한다.
- 감성 점수와 이벤트 유형 피처를 만든다.
- 급등/급락 이벤트 화면과 리포트 생성 흐름에 연결한다.

산출물:

- 외부 문서 수집 구조
- document metadata
- chunking/embedding pipeline
- vector index
- 종목/날짜별 외부 요인 요약
- sentiment/event feature
- Electron Events/Reports 연결 구조

학습 포인트:

- RAG
- 문서 chunking
- embedding
- vector index
- sentiment feature
- 외부 요인과 가격 데이터 결합
- AI 분석 결과를 제품 화면에 연결하는 방식

## Phase 9: 로컬 운영 구조를 AWS로 이전

목표:

- 서버2 파일 저장소 구조를 S3 bucket 구조로 이전한다.
- 서버2 PostgreSQL 메타데이터 DB를 RDS PostgreSQL로 이전한다.
- provider, symbol, date/year 기준 파티션 구조를 유지한다.
- 기존 `ssh://` 또는 local path 기반 `storage_uri`를 `s3://` URI 구조로 바꾼다.
- 로컬과 AWS storage provider를 설정으로 전환할 수 있게 만든다.
- IAM, security group, 비용 관리 기준을 정리한다.

산출물:

- S3 bucket/prefix 설계
- RDS PostgreSQL schema
- IAM 권한 설계
- security group 설계
- storage provider 전환 코드
- migration runbook
- 비용 점검표

학습 포인트:

- S3 bucket
- object storage
- data lake
- RDS PostgreSQL
- IAM과 보안 그룹
- local path와 `s3://` URI 전환
- 로컬 서버 구조를 managed service로 옮기는 사고방식

## Phase 10: SageMaker와 운영 관찰성

목표:

- Airflow에서 SageMaker Training Job을 실행한다.
- S3의 processed feature 데이터를 읽어 학습한다.
- 모델 산출물과 평가 지표를 다시 S3/RDS에 기록한다.
- CloudWatch 로그, 실패 알림, 재시도 정책, 백업 정책을 확인한다.
- 로컬 Airflow 운영 경험과 AWS 관리형 서비스 운영 경험을 비교한다.

산출물:

- SageMaker training script
- Airflow SageMaker task
- S3 model artifact
- RDS model metadata
- CloudWatch log 확인 절차
- 운영 점검 체크리스트

학습 포인트:

- SageMaker Training Job
- managed training
- Airflow와 AWS 서비스 연동
- CloudWatch
- 운영 관찰성
- 백업과 장애 대응
- 비용과 운영 복잡도 비교

## Phase 글 기록 템플릿

- 날짜:
- 이번 Phase 목표:
- 이전 Phase까지의 상태:
- 설계 선택:
- 사용한 데이터 소스:
- 구현한 구조:
- 실행한 명령어:
- 검증 방법:
- 구현 결과:
- 실패한 점:
- 해결 방법:
- 남은 한계:
- 인프라 관점에서 배운 점:
- 포트폴리오에서 설명할 문장:
