# ChartMaster Phase별 기술 블로그 기록 템플릿

이 문서는 ChartMaster 프로젝트를 기술 블로그에 시리즈로 정리하기 위한 글쓰기 구조다.

첫 번째 글은 프로젝트 전체 개요와 명세서 역할을 한다. 두 번째 글부터는 Phase별 구현 기록을 남긴다.

## 전체 시리즈 구조

추천 시리즈 구성은 다음과 같다.

```text
Post 1. 주식 시장 데이터 기반 Data Engineering/MLOps 프로젝트 개요와 설계
Post 2. Phase 1 - 시장 데이터 백필과 서버2 저장 구조
Post 3. Phase 2 - Airflow 기반 장마감 후 일봉 자동 수집
Post 4. Phase 3 - Electron Dashboard UI 설계와 Mock Prototype
Post 5. Phase 4 - FastAPI 데이터 제공 계층과 서비스 경계 설계
Post 6. Phase 5 - 데이터 품질, 백필, 재처리 전략
Post 7. Phase 6 - 운영 안정성과 백업/복구 설계
Post 8. Phase 7 - 머신러닝 모델 학습 파이프라인
Post 9. Phase 8 - RAG와 외부 요인 분석 계층
Post 10. Phase 9 - 로컬 운영 구조를 AWS로 이전
Post 11. Phase 10 - SageMaker와 운영 관찰성
```

## Phase 글 기본 템플릿

각 Phase 글은 같은 구조로 작성한다.

```text
1. 이번 Phase의 목표
2. 이전 Phase까지의 상태
3. 이번 Phase에서 구현한 구조
4. 사용 기술
5. 구현 과정
6. 실행한 명령어
7. 결과 확인
8. 발생한 문제
9. 해결 과정
10. 배운 개념
11. 포트폴리오에서 설명할 수 있는 문장
12. 다음 Phase로 넘길 과제
```

이 템플릿을 쓰면 단순한 작업 기록이 아니라, 문제 정의, 설계, 구현, 검증, 회고가 모두 포함된 글이 된다.

## Post 2. Phase 1 - 시장 데이터 백필과 서버2 저장 구조

### 글의 목적

Phase 1 글은 ChartMaster의 첫 번째 실제 구현 기록이다.

이 글에서는 Airflow나 AWS로 가기 전에 먼저 로컬 Python ETL이 정상적으로 데이터를 수집하고, 서버2 파일 저장소와 PostgreSQL에 기록할 수 있는지 검증한 과정을 정리한다.

### 포함할 내용

```text
1. Phase 1 목표
2. 왜 Airflow보다 로컬 ETL을 먼저 만들었는가
3. assets.json으로 종목 목록 관리
4. yfinance로 OHLCV 백필
5. 서버2 raw/processed 저장 구조
6. PostgreSQL metadata 테이블
7. 기본 피처 생성
8. WDC 추가와 SNDK experimental 이동
9. pykrx/Stooq 조사 결과
10. Phase 1 결과와 한계
```

### 핵심 설명 포인트

Airflow를 먼저 붙이지 않고 로컬 ETL을 먼저 만든 이유를 설명한다.

```text
Airflow는 파이프라인을 스케줄링하고 로그/실패/재시도를 관리하는 도구이지, 데이터 처리 로직 자체를 대신 만들어주는 도구는 아니다. 따라서 먼저 Python ETL 스크립트가 수동 실행으로 정상 동작하는지 확인한 뒤, 그 스크립트를 Airflow DAG로 감싸는 순서로 진행했다.
```

서버1과 서버2 역할을 다시 설명한다.

```text
서버1은 ETL을 실행하고, 서버2는 데이터와 메타데이터를 저장한다.
```

파일 저장소와 PostgreSQL의 차이를 설명한다.

```text
실제 OHLCV 데이터와 피처 데이터는 서버2 파일 저장소에 CSV로 저장하고, PostgreSQL에는 파일 위치, row count, 날짜 범위, 실행 이력을 기록했다.
```

### Phase 1 결과 예시

```text
총 수집 종목: 미국 대형주/ETF 확장 후 29개
국내 core:
  000660.KS
  005930.KS
  022100.KS
  005380.KS
  005490.KS
  000810.KS
  066570.KS
  034730.KS
  030200.KS
  015760.KS
  055550.KS
  105560.KS

미국 core:
  MU
  WDC
  SPY
  QQQ
  AAPL
  MSFT
  IBM
  KO
  JPM
  XOM
  CAT
  PG

experimental:
  SNDK
  SOXL
  NASA
  SPCX
  RAM
```

### 배운 개념

```text
yfinance 사용법
OHLCV 데이터 구조
상장일과 데이터 제공 시작일의 차이
raw/processed 데이터 분리
파일 저장소와 metadata DB 분리
PostgreSQL schema 설계
서버 간 SSH 기반 파일 저장
가상환경 사용 이유
```

### 포트폴리오 문장

```text
Phase 1에서는 yfinance 기반 OHLCV 백필 파이프라인을 구현하고, 서버2 파일 저장소와 PostgreSQL 메타데이터 DB를 분리해 데이터셋 위치와 실행 이력을 관리했습니다. 이 과정에서 실제 데이터는 파일 저장소에, 상태와 이력은 DB에 저장하는 구조를 설계했습니다.
```

## Post 3. Phase 2 - Airflow 기반 장마감 후 일봉 자동 수집

### 글의 목적

Phase 2 글은 Airflow를 실제 운영 흐름에 붙인 기록이다.

단순히 DAG 파일을 만든 것이 아니라, Docker Compose로 Airflow를 띄우고, 서버 재부팅 시 자동으로 올라오게 하고, 한국장과 미국장 장마감 시간을 고려해 자동 수집되도록 만든 과정을 정리한다.

### 포함할 내용

```text
1. Phase 2 목표
2. Airflow가 필요한 이유
3. Docker Compose 구성
4. 한국장/미국장 DAG 분리
5. 장마감 후 실행 시간 설계
6. catchup=True를 둔 이유
7. 최근 10일 overlap 수집 전략
8. merge/dedup으로 기존 백필 데이터 보호
9. Docker 권한 문제 해결
10. Airflow UID 문제 해결
11. start_date 문제 해결
12. 첫 자동 수집 성공 결과
```

### 핵심 설명 포인트

Airflow의 역할을 명확히 설명한다.

```text
Airflow는 데이터를 직접 수집하는 라이브러리가 아니라, 정해진 시간에 ETL 코드를 실행하고, 실행 상태, 로그, 실패, 재시도, catchup을 관리하는 오케스트레이션 도구다.
```

한국장과 미국장 DAG를 분리한 이유를 설명한다.

```text
한국장과 미국장은 장 마감 시간이 다르기 때문에 하나의 DAG로 묶기보다 시장별 DAG로 분리했다. 한국장은 Asia/Seoul 기준 평일 16:10, 미국장은 America/New_York 기준 평일 17:30에 실행되도록 했다.
```

최근 10일 overlap 수집 전략을 설명한다.

```text
일봉 데이터는 장마감 직후 바로 완전하게 반영되지 않을 수 있고, 거래량이나 수정주가가 나중에 정정될 수 있다. 또한 서버가 꺼져 있으면 며칠치 실행이 누락될 수 있다. 그래서 매일 최근 10일치를 다시 수집하고, 기존 데이터와 날짜 기준으로 병합했다.
```

중복 처리 설명:

```text
기존 데이터와 새 데이터를 합친 뒤 date 기준으로 중복을 제거했다. 같은 날짜가 있으면 새로 받은 row를 유지하도록 했다.
```

### 실제 성공 결과

```text
DAG: daily_kr_market_data_etl
상태: success
실행 시각: 2026-07-28 16:11 KST
수집 범위: 2026-07-17 ~ 2026-07-28
대상:
  000660.KS
  005930.KS
  022100.KS
  005380.KS
  005490.KS
  000810.KS
  066570.KS
  034730.KS
  030200.KS
  015760.KS
  055550.KS
  105560.KS
저장:
  서버2 raw
  서버2 processed
  서버2 PostgreSQL metadata
```

### 발생한 문제와 해결

#### Docker 권한 문제

```text
permission denied while trying to connect to the Docker daemon socket
```

원인:

```text
현재 터미널 세션이 docker 그룹 권한을 들고 있지 않았다. /etc/group에는 dnhs01이 docker 그룹에 등록되어 있었지만, 이미 열린 세션에는 그룹 변경이 반영되지 않았다.
```

해결:

```bash
sg docker -c 'docker compose --env-file ../.env up -d --build'
```

정식 해결:

```bash
newgrp docker
```

또는 로그아웃 후 재로그인.

#### Airflow UID 문제

원인:

```text
컨테이너를 UID 1000으로 실행했지만, Airflow 이미지 내부에 UID 1000에 해당하는 사용자 이름이 없었다.
```

에러:

```text
The user that Airflow is running as has no username
```

해결:

```dockerfile
USER root
RUN useradd --uid 1000 --gid 0 --home-dir /home/dnhs01 --create-home --shell /bin/bash dnhs01

USER airflow
```

#### Airflow start_date 문제

원인:

```text
Airflow start_date는 즉시 실행 시각이 아니라 schedule interval 계산 기준이다. 현재 날짜로 잡으면 기대한 시점에 바로 첫 run이 생기지 않을 수 있다.
```

해결:

```python
start_date=pendulum.datetime(2026, 7, 27, tz="Asia/Seoul")
```

### 배운 개념

```text
Airflow DAG
schedule
catchup
max_active_runs
BashOperator
Airflow metadata DB
Docker Compose
restart policy
Docker daemon socket
Linux group session
Airflow 컨테이너 UID
```

### 포트폴리오 문장

```text
Phase 2에서는 Airflow와 Docker Compose를 이용해 한국장/미국장 일봉 수집 파이프라인을 자동화했습니다. 장마감 시간을 고려해 DAG를 분리했고, 서버가 꺼져 있던 경우에도 catchup과 10일 overlap merge를 통해 누락과 데이터 정정을 흡수하도록 설계했습니다. 또한 Docker 권한 문제, Airflow 컨테이너 UID 문제, start_date 동작 문제를 실제 운영 과정에서 확인하고 해결했습니다.
```

## Post 4. Phase 3 - Electron Dashboard UI 설계와 Mock Prototype

구현을 완료했다. 실제 게시용 초안은 `04-phase3-electron-dashboard.md`에 분리했으며, 아래 항목은 작성 방향을 확인하는 체크리스트로 유지한다.

### 목표

```text
실제 모델, RAG, AI 리포트가 완성되기 전에 Electron 앱의 화면 구조와 사용자 흐름을 mock data 기반으로 먼저 고정한다.
```

### 포함할 내용

```text
1. 왜 데이터 검증/모델링보다 UI prototype을 먼저 만드는가
2. Electron을 선택한 이유
3. 전체 navigation 구조
4. Dashboard 화면
5. Assets 목록 화면
6. Asset Detail 화면
7. Pipelines 상태 화면
8. Models 화면
9. Reports 화면
10. Settings 화면
11. mock JSON 구조
12. 나중에 FastAPI와 연결할 데이터 shape
13. 전체 이력을 유지한 기간별 차트와 과거 탐색
14. 종목별 데이터 품질 이슈 상세
15. FastAPI 실데이터 연결과 컨테이너 UID 문제
```

### 포트폴리오 문장 후보

```text
데이터 품질 검증과 모델링이 계속 바뀔 수 있는 상황에서, 먼저 Electron Dashboard의 정보 구조와 화면 흐름을 mock data 기반으로 설계했습니다. 이를 통해 이후 FastAPI, 모델 결과, RAG 리포트가 어떤 형태로 앱에 연결되어야 하는지 API 계약을 역으로 정의할 수 있게 했습니다.
```

## Post 5. Phase 4 - FastAPI 데이터 제공 계층과 서비스 경계 설계

### 목표

```text
Electron 앱이 직접 파일 저장소나 PostgreSQL에 접근하지 않도록 FastAPI 계층을 두고, mock data와 live data를 같은 API shape으로 연결할 준비를 한다.
```

### 포함할 내용

```text
1. 왜 Electron이 DB에 직접 붙으면 안 되는가
2. FastAPI의 역할
3. Phase 3 mock JSON을 API contract로 바꾸는 방법
4. /assets
5. /assets/{symbol}
6. /pipelines
7. /models
8. /reports
9. mock provider와 live provider 분리
10. 서버1 API 계층과 서버2 데이터 저장소의 연결 지점
11. 환경변수, API URL, DB 접속 정보 관리
12. 리눅스 기초 구조는 별도 인프라 프로젝트에서 다루고, 여기서는 서비스 경계에 집중한다는 설명
```

### 포트폴리오 문장 후보

```text
Electron UI가 데이터 저장소 구조에 직접 의존하지 않도록 FastAPI 계층을 설계하고, mock data와 live data가 같은 응답 형태를 사용하도록 API contract를 정의했습니다. 이를 통해 클라이언트, API, 데이터 저장소의 책임을 분리했습니다.
```

## Post 6. Phase 5 - 데이터 품질, 백필, 재처리 전략

### 목표

```text
종목 유니버스와 데이터 소스별 커버리지를 검증하고, 누락/중복/정정 데이터에 대응할 수 있는 백필과 재처리 전략을 정리한다.
```

### 포함할 내용

```text
1. 왜 종목 수를 늘렸는가
2. 국내장/미국장 universe 선정 기준
3. yfinance, pykrx, Stooq 커버리지 비교
4. 상장일과 최초 수집 가능일 차이
5. 신규 상장 종목과 ETF를 experimental tier로 분리하는 이유
6. 누락 데이터 확인
7. 중복 데이터 확인
8. 날짜 범위와 row count 검증
9. 백필 재실행 절차
10. 실패 데이터 재처리 절차
11. idempotent ETL의 의미
12. 종목 수 증가 시 Airflow 실행 시간과 실패 처리
```

### 포트폴리오 문장 후보

```text
국내장과 미국장 종목 유니버스를 확장하면서 데이터 소스별 커버리지와 상장 이력 차이를 검증했습니다. 누락과 중복을 점검하고, 백필과 재처리를 반복해도 결과가 깨지지 않도록 idempotent ETL 관점에서 수집 구조를 정리했습니다.
```

## Post 7. Phase 6 - 운영 안정성과 백업/복구 설계

### 목표

```text
데이터 수집이 한 번 성공하는 것을 넘어서, 장애가 나도 확인하고 복구할 수 있는 운영 절차를 만든다.
```

### 포함할 내용

```text
1. 왜 백업과 복구를 별도 Phase로 두는가
2. 서버2 raw/processed 파일 저장소 백업
3. PostgreSQL metadata DB backup
4. PostgreSQL restore 테스트
5. Airflow DAG 실패 확인
6. Airflow 수동 재실행
7. Docker 컨테이너 재시작 확인
8. 서버 재부팅 후 자동 복구 확인
9. 네트워크 일시 장애 시 확인할 항목
10. 로그 확인 절차
11. 운영 점검 체크리스트
```

### 포트폴리오 문장 후보

```text
데이터 파이프라인을 단순히 실행하는 데서 끝내지 않고, 파일 저장소와 PostgreSQL metadata DB의 백업/복구 절차, Airflow 실패 대응, 서버 재시작 후 자동 복구 확인 절차를 runbook 형태로 정리했습니다.
```

## Post 8. Phase 7 - 머신러닝 모델 학습 파이프라인

### 목표

```text
processed feature 데이터를 이용해 첫 baseline 모델을 학습하고, 이후 Airflow 재학습으로 확장 가능한 모델 학습 파이프라인을 만든다.
```

### 포함할 내용

```text
1. 예측 문제 정의
2. target_positive_5d_return
3. naive baseline
4. train/validation split
5. time series split
6. leakage 방지
7. 모델 metric
8. model artifact 저장
9. model_versions/model_metrics 테이블
10. 이후 weekly_model_training DAG로 확장하는 구조
```

### 포트폴리오 문장 후보

```text
processed feature 데이터를 기반으로 첫 baseline 모델을 학습하고, naive baseline과 비교해 모델이 실제로 의미 있는 신호를 학습하는지 검증했습니다. 모델 artifact와 metric을 분리 저장해 이후 Airflow 기반 재학습 자동화로 확장할 수 있는 기준선을 만들었습니다.
```

## Post 9. Phase 8 - RAG와 외부 요인 분석 계층

### 목표

```text
가격 데이터만으로 설명하기 어려운 외부 요인을 RAG와 문서 분석 계층으로 보강한다.
```

### 포함할 내용

```text
1. 가격 데이터만 사용할 때의 한계
2. 뉴스/리포트/매크로 이벤트 수집
3. raw external_documents 저장
4. 문서 정제와 chunking
5. embedding
6. vector index
7. RAG 요약
8. 감성 점수
9. 이벤트 분류
10. 일별 종목 feature로 결합
11. 급등/급락 이벤트 화면과 연결
12. AI 리포트 흐름과 연결
```

### 포트폴리오 문장 후보

```text
주가 데이터만으로 설명하기 어려운 시장 변동 요인을 보강하기 위해 뉴스와 리포트를 수집하고, RAG 기반 요약과 감성 분석을 통해 일별 외부 요인 feature를 생성하는 계층을 설계했습니다.
```

## Post 10. Phase 9 - 로컬 운영 구조를 AWS로 이전

### 목표

```text
서버2 파일 저장소와 PostgreSQL 메타데이터 DB를 AWS S3/RDS 구조로 이전한다.
```

### 포함할 내용

```text
1. 왜 AWS를 뒤로 미뤘는가
2. 서버2 파일 저장소와 S3의 대응 관계
3. 서버2 PostgreSQL과 RDS의 대응 관계
4. bucket/prefix/partition 설계
5. storage_uri를 ssh://에서 s3://로 전환
6. 로컬과 AWS storage provider를 설정으로 전환하는 방법
7. IAM 권한
8. 보안 그룹
9. 비용 관리
10. 로컬 운영 구조와 managed service의 차이
```

### 포트폴리오 문장 후보

```text
로컬 서버2에서 검증한 raw/processed/metadata 구조를 AWS S3/RDS로 이전하면서, 저장소 구현은 바뀌어도 데이터 계층과 메타데이터 계약은 유지되도록 설계했습니다.
```

## Post 11. Phase 10 - SageMaker와 운영 관찰성

### 목표

```text
로컬 학습 코드를 SageMaker Training Job으로 확장하고, CloudWatch 기반 로그와 실패 처리를 확인한다.
```

### 포함할 내용

```text
1. 왜 SageMaker를 쓰는가
2. 로컬 학습과 managed training의 차이
3. S3 입력 데이터
4. Training Job 실행
5. output artifact
6. Airflow에서 SageMaker 호출
7. job status polling
8. CloudWatch 로그
9. 실패 처리와 재시도
10. 백업 정책
11. 비용과 운영 복잡도 비교
```

### 포트폴리오 문장 후보

```text
Airflow에서 SageMaker Training Job을 트리거하고, S3의 processed feature 데이터를 입력으로 사용해 모델을 학습한 뒤, 산출물과 평가 결과를 다시 S3/RDS에 기록했습니다. CloudWatch 로그와 실패 처리까지 확인해 로컬 운영과 AWS 관리형 운영의 차이를 비교했습니다.
```

## 글 작성 원칙

기술 블로그 글은 단순히 "무엇을 했다"가 아니라 다음 흐름을 보여주는 것이 좋다.

```text
왜 이 구조가 필요했는가
어떤 선택지가 있었는가
왜 이 선택을 했는가
구현하면서 어떤 문제가 생겼는가
어떻게 원인을 확인했는가
어떻게 해결했는가
이 경험으로 어떤 개념을 배웠는가
```

특히 포트폴리오에서는 실패와 해결 과정이 중요하다. Docker 권한 문제, Airflow UID 문제, start_date 문제처럼 실제로 운영하면서 부딪힌 문제는 좋은 글감이다.

## 공통 마무리 문장 템플릿

각 Phase 글 마지막에는 다음 형식으로 정리한다.

```text
이번 Phase에서는 [목표]를 구현했다.
핵심적으로 [기술/구조]를 사용했고,
[문제]를 겪었지만 [해결 방법]으로 해결했다.
이제 다음 Phase에서는 [다음 목표]로 확장할 예정이다.
```

예:

```text
이번 Phase에서는 Airflow를 이용해 한국장/미국장 일봉 수집을 자동화했다. 핵심적으로 Docker Compose, Airflow DAG, catchup, 10일 overlap merge 전략을 사용했고, Docker 권한 문제와 Airflow UID 문제를 겪었지만 그룹 세션과 컨테이너 사용자 추가로 해결했다. 이제 다음 Phase에서는 데이터 품질 검증이나 모델링으로 바로 들어가기보다, Electron Dashboard UI와 mock prototype을 먼저 만들어 이후 결과물이 들어갈 화면 구조를 고정할 예정이다.
```
