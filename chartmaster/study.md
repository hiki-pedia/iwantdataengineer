# chartmaster
개요: sk하이닉스, 삼성전자, 포스코 dx, 현대자동차, 마이크론, 샌디스크, soxl(미국 반도체 3배), nasa, spacex, ram(하이닉스 삼전 마이크론 등 2배 etf)의 주식을 airflow로 매일 지정된 시간에 데이터를 가져온다. 이를 종합해 앞으로 주식 변동성을 확인하고 예측한다. 이를 Electron로 보여준다

## 프로젝트 방향 정리

ChartMaster는 단순히 주식 앱을 만드는 프로젝트가 아니라, 데이터 엔지니어링과 MLOps를 공부하기 위한 학습형 포트폴리오 프로젝트다.

핵심 목표는 다음과 같다.

- 주식 데이터를 정기적으로 수집한다.
- 원본 데이터와 가공 데이터를 분리해서 저장한다.
- Airflow로 ETL 파이프라인을 자동화한다.
- PostgreSQL로 메타데이터와 실행 이력을 관리한다.(서버2에 저장한다.)
- 이후 AWS S3, RDS, SageMaker로 확장한다.(여기서 서버2는 aws로 완전히 대체된다.)
- AI/RAG/딥러닝을 이용해 외부 요인 분석과 예측 모델 실험을 한다.
  단순히 차트를 분석하는 것에서 끝나는 것이 아니라 해당 시점에 해당하는 뉴스나 사건들을 검색, 그리고 실적발표등을 고려해서 파악을 해본다. 해당 시점에서 여론은 어땠는지 그리고 그 여론이 사람들의 심리를 어떻게 자극했고 그 결과. 예시로 물타기가 심해 실적발표 전 기대치 선 반영으로 실제로 주가가 큰 폭으로 오르지 않음. 또한 미-이 전쟁 러-우 전쟁과 같은 외적인 요소들이 주가를 어떻게 반영했는지도 분석해본다. - 데이터를 모으고 분석하는 중요한 단계가 된다.
- Electron 앱에서 차트, 예측 결과, 모델 이력, AI 분석 리포트를 확인한다.

## 사용하는 자산

초기 자산은 한국장과 미국장으로 나눈다.

한국장 core:

- `000660.KS`: SK하이닉스
- `005930.KS`: 삼성전자
- `022100.KQ`: 포스코DX
- `005380.KS`: 현대차

미국장 core:

- `MU`: Micron Technology
- `SNDK`: SanDisk

실험 자산:

- `SOXL`: 미국 반도체 3배 레버리지 ETF
- `NASA`: 우주 산업 ETF
- `SPCX`: SpaceX 관련 자산
- `RAM`: DRAM 2배 레버리지 ETF

core 자산은 첫 모델 학습에 사용하고, experimental 자산은 먼저 데이터 수집과 시각화부터 확인한다. 레버리지 ETF나 신규 ETF는 데이터 기간이 짧거나 구조가 복잡해서 초기 모델 학습에는 부적합할 수 있다.

## yfinance와 OHLCV

`yfinance`는 Yahoo Finance 데이터를 Python에서 가져올 수 있게 해주는 라이브러리다. 첫 실습 단계에서는 무료로 쓰기 쉽고 접근성이 좋아서 사용한다.

OHLCV는 주식 시장 데이터의 기본 형태다.

- `Open`: 시가
- `High`: 고가
- `Low`: 저가
- `Close`: 종가
- `Volume`: 거래량

예측 모델이나 피처 엔지니어링은 보통 이 OHLCV 데이터에서 시작한다.


## 서버1과 서버2 역할

현재 홈서버 단계에서는 서버1과 서버2 역할을 나눈다.

서버1:

- 개발 작업
- Airflow 실행
- ETL 코드 실행
- yfinance 데이터 수집
- 피처 생성
- 서버2 저장소와 PostgreSQL에 저장 요청

서버2:

- 파일 저장소 역할
- PostgreSQL DB 역할
- 프로젝트별 데이터 영역 분리
- 이후 AWS의 S3와 RDS를 이해하기 위한 미니 AWS 역할

서버2에 ChartMaster 실행 코드를 둘 필요는 없다. 서버2는 데이터 저장과 DB 역할만 한다.

## 파일 저장소와 PostgreSQL 차이

파일 저장소는 실제 데이터 덩어리를 보관하는 곳이다.

예:

```text
/data/chartmaster/raw/market_data/provider=yfinance/symbol=005930.KS/year=2024/data.parquet
```

여기에는 실제 OHLCV 데이터나 피처 데이터가 들어간다.

PostgreSQL은 그 데이터 파일의 주소, 상태, 이력, 관계를 관리하는 장부 역할을 한다.

예:

```text
datasets 테이블
- dataset_type: raw_market_data
- symbol: 005930.KS
- storage_uri: /data/chartmaster/raw/...
- row_count: 245
- start_date: 2024-01-02
- end_date: 2024-12-30
- created_at: 2026-07-24 15:00:00
```

정리하면:

```text
파일 저장소 = 실제 데이터 보관
PostgreSQL = 데이터의 위치, 상태, 실행 이력 관리
```

이 구조를 쓰면 데이터가 커져도 원본/가공/학습 데이터를 파일 저장소에 둘 수 있고, DB는 메타데이터 관리에 집중할 수 있다.

## 서버2 저장소 구조

서버2에는 ChartMaster 전용 데이터 영역을 만든다.

```text
/data/chartmaster/
  raw/
  processed/
  curated/
  models/
  reports/
  logs/
  backups/
```

각 폴더 역할:

- `raw`: yfinance 등에서 받은 원본 데이터
- `processed`: 기본 피처를 생성한 가공 데이터
- `curated`: 모델 학습용으로 최종 정리한 데이터셋
- `models`: 학습된 모델 파일
- `reports`: AI 분석 리포트
- `logs`: ETL 실행 로그
- `backups`: DB 백업 또는 중요 파일 백업

이 구조는 나중에 S3로 옮기기 쉽다.

## AWS로 넘어가면 바뀌는 것

현재 서버2는 학습용 미니 AWS 역할을 한다.

```text
서버2 파일 저장소 -> AWS S3
서버2 PostgreSQL -> AWS RDS PostgreSQL
서버1 Airflow/실행 환경 -> EC2 또는 MWAA
모델 학습 실행 -> SageMaker
로그/운영 관찰 -> CloudWatch
```

즉 서버2는 최종 AWS 단계에서는 거의 대체된다. 하지만 먼저 서버2에서 직접 구조를 만들어 보면 S3와 RDS가 왜 필요한지 이해하기 쉽다.

중요한 설계 포인트는 `storage_uri`를 바꾸기 쉬운 형태로 관리하는 것이다.

현재:

```text
storage_uri = /data/chartmaster/raw/market_data/provider=yfinance/symbol=005930.KS/year=2024/data.parquet
```

AWS 이후:

```text
storage_uri = s3://chartmaster-dev/raw/market_data/provider=yfinance/symbol=005930.KS/year=2024/data.parquet
```

## Airflow와 DAG

Airflow는 정해진 시간에 데이터 파이프라인을 실행하고, 실패/재시도/로그를 관리하는 워크플로우 도구다.

DAG는 Directed Acyclic Graph의 약자다. Airflow에서 하나의 파이프라인을 정의하는 단위다.

예:

```text
daily_market_data_etl
  -> 자산 목록 읽기
  -> 시장 데이터 수집
  -> raw 저장
  -> 피처 생성
  -> processed 저장
  -> PostgreSQL 메타데이터 기록
```

첫 구현에서는 Airflow보다 먼저 로컬 ETL 스크립트가 정상 동작하는지 확인하고, 그 다음 Airflow DAG로 감싸는 것이 좋다.

## AI 활용 방향

AI는 투자 결정을 대신하는 용도가 아니라, 예측 결과를 해석하고 외부 요인을 정리하는 보조 도구로 사용한다.

AI 사용 후보:

- RAG: 뉴스/리포트/매크로 문서를 검색하고 요약
- 감성 분석: 뉴스 텍스트를 긍정/부정/중립 점수로 변환
- 이벤트 분류: 실적, 규제, 공급망, 금리/환율, 경쟁사 이슈 등으로 분류
- 딥러닝: LSTM/GRU/Transformer로 시계열 모델 실험
- AI 리포트: 예측 결과, 외부 요인, 모델 신뢰도, 데이터 한계를 요약

AI 리포트는 투자 추천 문구를 포함하지 않는다.

## 구현 순서

처음 만들어야 할 것은 예측 모델이나 AI가 아니라 데이터 수집과 저장까지 되는 최소 파이프라인이다.

1. `assets.json`에서 종목 목록을 읽는다.
2. yfinance로 OHLCV 데이터를 수집한다.
3. 서버2 파일 저장소의 `raw` 영역에 원본 데이터를 저장한다.
4. 기본 피처를 생성한다.
5. 서버2 파일 저장소의 `processed` 영역에 피처 데이터를 저장한다.
6. PostgreSQL에 데이터셋 메타데이터와 실행 이력을 기록한다.
7. 이 흐름이 안정되면 Airflow DAG로 자동화한다.
8. 이후 baseline ML, S3/RDS, SageMaker, RAG/AI 순서로 확장한다.

## 지금 이해해야 할 핵심 문장

```text
서버1은 실행하고, 서버2는 저장한다.
파일 저장소는 실제 데이터를 담고, PostgreSQL은 데이터의 주소와 이력을 관리한다.
서버2 파일 저장소는 나중에 S3로, 서버2 PostgreSQL은 나중에 RDS로 대체된다.
첫 목표는 예측이 아니라 수집-저장-가공 파이프라인을 반복 가능하게 만드는 것이다.
```

## 기본 피처

피처는 모델이 학습할 수 있도록 원본 데이터에서 계산한 입력값이다. 이것은 이후에 바뀔 수 있다. 

기본 피처 후보:

- `turnover_value = close * volume`
- `return_1d = 오늘 종가 / 1거래일 전 종가 - 1`
- `return_5d = 오늘 종가 / 5거래일 전 종가 - 1`
- `return_20d = 오늘 종가 / 20거래일 전 종가 - 1`
- `volume_change_1d = 오늘 거래량 / 1거래일 전 거래량 - 1`
- `moving_average_5 = 최근 5거래일 종가 평균`
- `moving_average_20 = 최근 20거래일 종가 평균`
- `volatility_5 = 최근 5거래일 수익률 표준편차`
- `volatility_20 = 최근 20거래일 수익률 표준편차`

초기 예측 타깃은 정확한 종가 예측이 아니라 이진 분류로 둔다.

```text
target_positive_5d_return = 5거래일 뒤 수익률이 0보다 큰가?
```

이렇게 하면 “5거래일 뒤 오를지 내릴지”를 예측하는 문제로 단순화할 수 있다.
이것은 단순히 차트를 분석하는 1단계 괴정이다.

## 개발 리포트

오늘 한 일
배운 개념
실패/해결
다음 할 일
포트폴리오 설명 문장

### phase1

#### 서버1

서버1은 ChartMaster의 실행 서버이자 개발 서버다. 실제 데이터 파일을 보관하는 서버가 아니라, 코드를 실행해서 서버2의 파일 저장소와 PostgreSQL에 결과를 보내는 역할을 한다.

서버1의 기본 구조:

```text
~/iwantdataengineer/
  .env
  .env.example
  .gitignore
  README.md
  chartmaster/
    README.md
    ProductSpec.md
    TechSpec.md
    study.md
    requirements.txt
    config/
      assets.json
    docs/
      architecture.md
      learning-roadmap.md
      ai-plan.md
    src/
      chartmaster/
        config.py
        data/
        features/
        models/
        pipelines/
        storage/
        ai/
        rag/
    .venv/
```

각 영역의 역할:

- `.env`: 서버2 SSH 접속 정보, PostgreSQL 접속 정보, API key 같은 민감한 설정을 저장한다. Git에 올리지 않는다.
- `chartmaster/config/assets.json`: 수집할 종목 목록과 core/experimental 구분을 저장한다.
- `chartmaster/src/chartmaster/data`: yfinance 같은 외부 데이터 제공자에서 OHLCV를 가져오는 코드가 들어간다.
- `chartmaster/src/chartmaster/features`: raw OHLCV 데이터에서 수익률, 이동평균, 변동성 같은 피처를 생성하는 코드가 들어간다.
- `chartmaster/src/chartmaster/pipelines`: 실제 실행 흐름을 묶는 코드가 들어간다. 현재는 `local_market_data_etl.py`가 시장 데이터 수집과 피처 생성을 실행한다.
- `chartmaster/src/chartmaster/storage`: 서버2 파일 저장소와 PostgreSQL metadata DB에 연결하는 코드가 들어간다.
- `chartmaster/src/chartmaster/models`: baseline 모델과 이후 딥러닝 모델 코드가 들어간다.
- `chartmaster/.venv`: ChartMaster 전용 Python 가상환경이다. pandas, yfinance, scikit-learn, psycopg 같은 의존성을 프로젝트별로 고정해서 사용한다.

현재 Phase 1 실행 흐름:

```text
서버1
  assets.json 읽기
  -> yfinance로 OHLCV 수집
  -> 기본 피처 생성
  -> SSH로 서버2 파일 저장소에 raw/processed CSV 저장
  -> PostgreSQL에 pipeline_runs/datasets metadata 기록
```

중요한 점:

```text
서버1에는 실제 데이터 산출물을 저장하지 않는다.
서버1은 실행만 하고, raw/processed/models 같은 결과 파일은 서버2 chartmaster 폴더에 저장한다.
PostgreSQL에는 실제 데이터가 아니라 파일 위치, 행 수, 실행 상태 같은 metadata를 기록한다.
```

서버1에서 실행한 백필 명령:

```bash
cd /home/dnhs01/iwantdataengineer

PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=chartmaster/src \
chartmaster/.venv/bin/python -m chartmaster.pipelines.local_market_data_etl \
  --tier all \
  --start 2000-01-01 \
  --end 2026-07-27
```

명령어 구성:

- `PYTHONDONTWRITEBYTECODE=1`: `__pycache__` 파일 생성을 막는다.
- `PYTHONPATH=chartmaster/src`: Python이 `chartmaster/src` 아래의 패키지를 찾게 한다.
- `chartmaster/.venv/bin/python`: 시스템 Python이 아니라 ChartMaster 전용 가상환경 Python으로 실행한다.
- `-m chartmaster.pipelines.local_market_data_etl`: ETL 파이프라인 모듈을 실행한다.
- `--tier all`: core와 experimental 자산을 모두 수집한다.
- `--start`, `--end`: 수집할 기간을 지정한다.

백필 결과:

```text
10개 자산 모두 수집 성공
서버2 raw 저장 완료
서버2 processed 저장 완료
PostgreSQL metadata 기록 완료
```
왜 가상환경을 써야하는가?
  로컬에 pandas 같은 패키지를 설치할 수는 있다 그런데 만약 로컬에서 서로 다른 프로젝트에서 같은 패키지에 대해서 다른 버전을 요구한다면 충돌이 발생한다. 또한 aws는 완전히 다른 컴퓨터이다 여기엔 이는 패키지가 그곳엔 없을 수 있다. 그래서 가상환경에 명령어로써 패키지 버전을 고정시킬 수 있다.


#### 서버2

~/iwantdataengineer/chartmaster 위치에 파일 저장소 역할의 파일들을 생성함. 실제 데이터들이 들어갈 공간임. docker에 postgreSQL을 깔았고 5432 포트로 열였음. 여기는 그 파일들의 목록/주소/상태를 기록할 db임. 
  raw/
  processed/
  curated/
  models/
  reports/
  logs/
  backups/
    postgres/
  postgres-data/
  docker/
    postgres/
      docker-compose.yml
이 구조로 만들었음. 

#### 공부한 내용

-p: port 또는 parents로 쓰임. 명령어마다 의미가 다름 "mkdir -p docker/postgres : 중간 폴더가 없어도 같이 만들어라." "docker run -p 5432:5432 postgres : 서버2의 5432로 접속하면 docker 컨테이너 안 postgreSQL 5432로 연결됨."
-d: 백그라운드에서 실행하라.
-U: PostgreSQL psql에서 user를 지정하는 옵션. psql -U chartmaster -d chartmaster : chartmater 유저로 접속한다. 여기서 -d는 chartmaster 데이터베이스에 접속한다. 
exec: 도커에서 명령어를 실행하는 명령어.

systemctl is-enabled docker 이 명령어의 결과가 enabled면 컴터가 켜지면 도커가 자동으로 올라옴.

### phase2

#### 서버1

한국장 마감 후 일봉 수집, 미국장 마감 후 일봉 수집. 최근 10일치 overlap으로 가져옴. 그리고 기존 cvs와 data 기준으로 머지
중복 날짜는 최신 row로 교체. 데이터는 서버 2에 저장. 서버가 꺼져있으면 서버가 다시 켜지고 스케줄러가 놓친 dag run을 만들어서 실행하고 날짜는 순서대로 처리하게 설정했음.

도커에 올려서 실행 시켰음. 이때 도커에서 문제가 발생했음
1. 도커 권한 문제.
permission denied while trying to connect to the Docker daemon socket
  현재 터미널 세션의 dnhs01이 그 소켓에 접근 권한이 없었다. root 또는 docker 그룹만 접근이 가능했다. 근데 내 세션이 그 그룹에 속해 있지 않았다. 일단은 그룹 권한을 가진 새 명령 세션으로 실행했다.
2. airflow 컨테이너 내부 사용자 문제
우리는 컨테이너 안에서 airflow를 uid 1000으로 실행하기로 했다. 하지만 airflow docker 이미지 안에는 해당하는 사용자 이름이 없었고 수정했다.

airflow는 정상 작동하고 접속은 http://10.0.0.1/8081이다.