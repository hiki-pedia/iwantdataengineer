# ChartMaster: 주식 데이터로 학습하는 Data Engineering/MLOps 프로젝트(Airflow와 AWS를 활용한 주식 데이터 기반 AI 분석 시스템)

## 1. 프로젝트 개요

ChartMaster는 주식 시장 데이터를 이용해 데이터 엔지니어링과 MLOps, AWS를 단계적으로 학습하기 위한 포트폴리오 프로젝트다.

이 프로젝트의 목적은 투자 추천 서비스를 만드는 것이 아니다. 핵심 목표는 시장 데이터를 매일 수집하고, 원본 데이터와 가공 데이터를 분리해서 저장하고, Airflow로 파이프라인을 자동화하고, PostgreSQL로 실행 이력과 데이터셋 메타데이터를 관리하는 전체 흐름을 직접 설계하고 운영해보는 것이다.

최종적으로는 로컬 홈서버 환경에서 만든 구조를 AWS 환경으로 확장한다. 서버2의 파일 저장소는 S3로, 서버2의 PostgreSQL은 RDS PostgreSQL로, 모델 학습은 SageMaker로 옮기는 것을 목표로 한다. 이후에는 뉴스, 리포트, 매크로 이벤트 같은 외부 요인을 RAG와 감성 분석으로 결합하고, Electron 데스크톱 애플리케이션에서 데이터와 모델 결과를 확인하는 방향으로 확장한다.

리눅스 사용자, 권한, 내부망, SSH 같은 서버 기초 구조는 별도 인프라 프로젝트에서 자세히 다룬다. 이 프로젝트에서는 그 서버 환경 위에서 데이터 플랫폼의 서비스 경계, 저장소 분리, 자동화, 백업/복구, 운영 관찰성을 어떻게 설계하는지에 집중한다.

정리하면 ChartMaster는 다음 질문에 답하기 위한 프로젝트다.

```text
시장 데이터가 매일 들어온다면,
그 데이터를 어떻게 안정적으로 수집하고,
어디에 어떤 형태로 저장하고,
어떻게 가공하고,
어떻게 모델 학습과 분석으로 연결할 것인가?
```

## 2. 프로젝트를 시작한 이유

처음에는 채용공고 데이터를 수집하는 ETL 프로젝트를 생각했다. 하지만 채용공고 데이터는 수집 가능한 데이터 양과 주제의 다양성이 제한적일 수 있고, 장기적으로 MLOps나 모델 재학습 자동화까지 확장하기에는 학습 소재가 다소 부족할 수 있다고 판단했다.

반면 주식 시장 데이터는 매일 갱신되고, 종목별로 장기간 데이터가 쌓이며, 가격 데이터 외에도 뉴스, 실적 발표, 산업 리포트, 금리, 환율, 전쟁, 규제, 공급망 이슈 같은 외부 요인을 연결할 수 있다. 즉 단순 ETL에서 끝나지 않고 데이터 엔지니어링, 모델링, MLOps, RAG, AI 리포트 생성까지 확장하기 좋은 주제다. 또한 주제가 단순하다는 특징이 있지만 오히려 그렇기 때문에 다른 사람들과 비교하며 객관적인 평가가 가능하다 생각했다.

그래서 프로젝트 주제를 채용공고 ETL에서 Airflow와 AWS를 활용한 주식 데이터 기반 AI 분석 시스템으로 바꿨다.

이 프로젝트에서 가장 중요한 것은 예측 정확도를 빠르게 높이는 것이 아니다. 먼저 데이터가 안정적으로 흐르는 구조를 만드는 것이 핵심이다.

```text
데이터 수집
-> 원본 저장
-> 가공 데이터 생성
-> 메타데이터 기록
-> Airflow 자동화
-> 모델 학습
-> 평가
-> 외부 요인 분석
-> 결과 시각화
```

이 흐름을 직접 만들고 기록하는 것이 포트폴리오의 핵심이다.

## 3. 프로젝트 목표

ChartMaster의 목표는 크게 네 가지다.

첫 번째 목표는 데이터 수집 파이프라인을 만드는 것이다.

한국장과 미국장 종목을 정해두고, 매일 장 마감 후 일봉 OHLCV 데이터를 수집한다. 한국장과 미국장은 장 마감 시간이 다르기 때문에 Airflow DAG도 분리한다. 서버가 꺼져 있어 정해진 시간을 놓쳤다면, 서버가 다시 켜졌을 때 Airflow catchup으로 놓친 실행을 복구하도록 한다.

두 번째 목표는 데이터 저장 구조를 설계하는 것이다.

실제 데이터 파일은 파일 저장소에 저장하고, PostgreSQL에는 데이터 파일의 위치와 실행 이력, row count, 날짜 범위 같은 메타데이터만 저장한다. 이 구조는 나중에 AWS S3와 RDS로 옮기기 쉽다.

세 번째 목표는 MLOps 흐름을 학습하는 것이다.

초기에는 간단한 baseline 모델로 시작한다. 정확한 종가를 예측하는 대신, 5거래일 뒤 수익률이 양수인지 예측하는 이진 분류 문제로 단순화한다. 이후에는 주기적 재학습, 모델 버전 관리, 모델 성능 기록, naive baseline 비교, 조건부 배포 같은 MLOps 개념을 붙인다.

네 번째 목표는 AI와 외부 요인 분석을 결합하는 것이다.

가격 데이터만으로 주가를 설명하기는 어렵다. 따라서 뉴스, 실적 발표, 반도체 업황, 환율, 금리, 전쟁, 규제, 공급망 이슈 같은 외부 요인을 수집하고, RAG와 감성 분석으로 요약/분류하는 계층을 추가한다. AI는 투자 결정을 대신하는 도구가 아니라 모델 결과와 시장 맥락을 설명하는 보조 도구로 사용한다.

## 4. 프로젝트가 아닌 것

ChartMaster는 투자 추천 서비스가 아니다.

이 프로젝트에서 생성되는 예측 결과나 AI 리포트는 투자 판단의 근거로 사용하기 위한 것이 아니라, 데이터 파이프라인과 모델링, 운영 자동화를 학습하기 위한 산출물이다.

다만 데이터 품질 검증과 모델링은 계속 반복될 수 있는 영역이다. 따라서 데이터가 완전히 안정되기를 기다리기보다, 먼저 Electron 앱에서 무엇을 보여줄지, 어떤 화면 흐름으로 볼지, FastAPI가 어떤 응답 형태를 제공해야 하는지 정한다. Phase 3에서는 실제 모델이나 RAG 결과가 없어도 mock data 기반으로 화면 구조와 API 계약을 먼저 고정한다.

## 5. 사용 기술

현재 사용하거나 사용할 예정인 기술은 다음과 같다.

```text
Language
- Python

Data Collection
- yfinance
- 이후 후보: KRX, FinanceDataReader, pykrx, data.go.kr, 유료 API

Workflow Orchestration
- Apache Airflow

Container
- Docker
- Docker Compose

Storage
- 서버2 파일 저장소
- 이후 AWS S3

Metadata Database
- PostgreSQL
- 이후 AWS RDS PostgreSQL

Machine Learning
- scikit-learn
- 이후 PyTorch 또는 TensorFlow 후보

MLOps / Cloud
- AWS S3
- AWS RDS
- AWS SageMaker
- CloudWatch

AI / RAG
- OpenAI API
- Embedding
- Vector index
- Sentiment analysis
- AI report generation

Frontend
- Electron Desktop Application
- 이후 FastAPI 연동
```

현재 구현의 중심은 Python, yfinance, Airflow, Docker Compose, 서버2 파일 저장소, PostgreSQL이다.

## 6. 서버 구조

초기 홈서버 환경에서는 서버1과 서버2를 분리한다.

```text
서버1
  -> 개발 환경
  -> Airflow 실행
  -> ETL 코드 실행
  -> yfinance 데이터 수집
  -> 피처 생성
  -> 모델 학습 실행
  -> 이후 FastAPI/Electron 개발

서버2
  -> 파일 저장소
  -> PostgreSQL
  -> 프로젝트별 데이터 영역
  -> 이후 AWS S3/RDS를 이해하기 위한 학습용 데이터 서버
```

서버1은 실행 서버다. 코드를 실행하고, Airflow scheduler와 webserver를 띄우고, yfinance에서 데이터를 가져오고, 피처를 생성한다.

서버2는 데이터 서버다. 서버2에는 ChartMaster 실행 코드를 둘 필요가 없다. 서버2는 데이터 파일과 PostgreSQL 메타데이터를 저장하는 역할을 한다.

이 구조를 나눈 이유는 AWS로 확장할 때 역할이 명확해지기 때문이다.

```text
서버2 파일 저장소 -> AWS S3
서버2 PostgreSQL -> AWS RDS PostgreSQL
서버1 Airflow 실행 환경 -> EC2 또는 MWAA
모델 학습 실행 -> SageMaker
운영 로그와 모니터링 -> CloudWatch
```

즉 서버2는 최종 구조에서는 완전히 AWS 관리형 서비스로 대체될 수 있다. 하지만 그 전에 직접 서버2를 구성해보면 S3와 RDS가 왜 필요한지, 파일 저장소와 데이터베이스의 역할이 왜 다른지 더 잘 이해할 수 있다.

## 7. 파일 저장소와 PostgreSQL의 차이

이 프로젝트에서 중요한 설계 원칙은 실제 데이터와 메타데이터를 분리하는 것이다.

파일 저장소는 실제 데이터 덩어리를 보관한다.

예를 들어 삼성전자 일봉 원본 데이터는 다음과 같은 위치에 저장된다.

```text
/home/dnhs02/iwantdataengineer/chartmaster/raw/market_data/provider=yfinance/symbol=005930.KS/data.csv
```

피처 생성이 끝난 데이터는 다음 위치에 저장된다.

```text
/home/dnhs02/iwantdataengineer/chartmaster/processed/features/symbol=005930.KS/data.csv
```

반면 PostgreSQL은 실제 주가 데이터를 모두 저장하는 곳이 아니다. PostgreSQL은 데이터의 위치와 상태를 기록하는 장부 역할을 한다.

예를 들어 `datasets` 테이블에는 다음과 같은 정보가 들어간다.

```text
dataset_type: raw_market_data
provider: yfinance
symbol: 005930.KS
storage_uri: ssh://dnhs02@192.168.0.9/home/dnhs02/iwantdataengineer/chartmaster/raw/...
row_count: 6640
start_date: 2000-01-04
end_date: 2026-07-27
created_at: 실행 시각
```

정리하면 다음과 같다.

```text
파일 저장소 = 실제 데이터 보관
PostgreSQL = 데이터 위치, 상태, 실행 이력 관리
```

이 구조를 사용하면 데이터가 커져도 PostgreSQL이 무거워지지 않는다. 또한 나중에 파일 저장소를 S3로 바꾸더라도 PostgreSQL의 `storage_uri`만 `s3://...` 형태로 바꾸면 전체 구조를 유지할 수 있다.

## 8. 서버2 저장소 구조

서버2에는 ChartMaster 전용 데이터 영역을 만든다.

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

각 폴더의 의미는 다음과 같다.

```text
raw
  yfinance, KRX, 뉴스 API 등에서 받은 원본 데이터

processed
  원본 데이터를 정제하거나 피처를 계산한 가공 데이터

curated
  모델 학습에 바로 사용할 수 있도록 최종 정리한 데이터셋

models
  학습된 모델 파일과 관련 산출물

reports
  AI 분석 리포트, 종목별 요약 문서

logs
  ETL 실행 로그 또는 운영 기록

backups
  DB 백업, 중요 파일 백업
```

초기에는 CSV를 사용하지만, 데이터가 커지면 Parquet로 바꾸는 것도 고려할 수 있다. 중요한 것은 `raw`, `processed`, `curated`를 분리하는 습관이다. 이 구분은 데이터 레이크 설계에서 자주 사용되는 구조와도 연결된다.

## 9. 데이터 소스

현재 메인 데이터 소스는 yfinance다.

yfinance는 Yahoo Finance 데이터를 Python에서 쉽게 가져올 수 있게 해주는 라이브러리다. 무료로 접근할 수 있고, 한국장과 미국장 종목을 모두 다룰 수 있으며, 학습 프로젝트의 초기 데이터 수집 도구로 사용하기 좋다.

현재 수집하는 데이터는 일봉 OHLCV다.

```text
Open: 시가
High: 고가
Low: 저가
Close: 종가
Adjusted Close: 수정종가
Volume: 거래량
```

초기에는 1975년부터 데이터를 요청했지만, 실제로 제공되는 시작 시점은 종목마다 달랐다.

예를 들어 국내 종목은 yfinance 기준으로 대체로 2000년부터 데이터가 제공되었다. 삼성전자도 1975년 상장 이후 전체 데이터가 내려오는 것은 아니었다. 이는 상장일과 데이터 제공자의 히스토리 제공 범위가 다르기 때문이다.

또한 SanDisk의 `SNDK`는 데이터 기간이 매우 짧았다. SanDisk가 최근 다시 상장된 맥락 때문에 장기 모델 학습에는 적합하지 않았다. 그래서 저장장치/NAND 산업 노출을 더 길게 보기 위해 Western Digital `WDC`를 core 자산에 추가하고, `SNDK`는 experimental 자산으로 내렸다.

데이터 소스 후보로 pykrx와 Stooq도 확인했다.

pykrx는 한국장 데이터 보강 후보였지만, 현재 확인한 방식에서는 2000년 이전 데이터를 가져오지 못했고, 최근 3000거래일 정도만 조회되는 한계가 있었다.

Stooq는 CSV 다운로드 구조가 있지만, 현재 자동 접근 시 브라우저 검증 또는 API key 흐름이 나타났고, KRX 지원도 명확하지 않았다. 따라서 현재 프로젝트의 메인 소스로 쓰기에는 적합하지 않다고 판단했다.

현재 판단은 다음과 같다.

```text
초기 메인 소스: yfinance
한국장 보강 후보: KRX, FinanceDataReader, data.go.kr
미국장 보강 후보: Tiingo, Alpha Vantage, Polygon, Stooq API key
```

## 10. 관리 대상 자산

현재 관리 대상 자산은 한국장과 미국장으로 나눈다.

한국장 core:

```text
000660.KS: SK hynix
005930.KS: Samsung Electronics
022100.KS: POSCO DX
005380.KS: Hyundai Motor
005490.KS: POSCO Holdings
000810.KS: Samsung Fire & Marine Insurance
066570.KS: LG Electronics
034730.KS: SK Inc.
030200.KS: KT
015760.KS: Korea Electric Power
055550.KS: Shinhan Financial Group
105560.KS: KB Financial Group
```

미국장 core:

```text
MU: Micron Technology
WDC: Western Digital
SPY: SPDR S&P 500 ETF Trust
QQQ: Invesco QQQ Trust
AAPL: Apple
MSFT: Microsoft
IBM: International Business Machines
KO: Coca-Cola
JPM: JPMorgan Chase
XOM: Exxon Mobil
CAT: Caterpillar
PG: Procter & Gamble
```

미국장 experimental:

```text
SNDK: SanDisk
SOXL: Direxion Daily Semiconductor Bull 3X ETF
NASA: Tema Space Innovators ETF
SPCX: SpaceX 관련 자산
RAM: Roundhill T-REX 2X Long DRAM Daily Target ETF
```

core와 experimental을 나눈 이유는 데이터 기간과 해석 가능성 때문이다.

core 자산은 첫 모델 학습과 평가에 사용할 만큼 데이터 기간이 충분하고 해석이 비교적 쉬운 자산이다. experimental 자산은 데이터 수집과 시각화에는 유용하지만, 상장 이력이 짧거나 ETF 구조가 복잡하거나 레버리지 ETF의 일일 리셋 구조 때문에 초기 모델 학습에는 부적합할 수 있다.

## 11. 기본 피처 설계

초기 모델은 OHLCV 데이터에서 기본 피처를 만든다.

현재 사용하는 기본 피처는 다음과 같다.

```text
turnover_value = close * volume
return_1d = 1거래일 수익률
return_5d = 5거래일 수익률
return_20d = 20거래일 수익률
volume_change_1d = 1거래일 거래량 변화율
moving_average_5 = 5거래일 이동평균
moving_average_20 = 20거래일 이동평균
volatility_5 = 최근 5거래일 수익률 표준편차
volatility_20 = 최근 20거래일 수익률 표준편차
```

초기 예측 타깃은 정확한 종가가 아니다. 종가를 직접 맞히는 것은 난이도가 높고, 학습 초반에는 평가와 설명이 어려울 수 있다. 대신 다음과 같은 이진 분류 문제로 시작한다.

```text
target_positive_5d_return = 5거래일 뒤 수익률이 0보다 큰가?
```

즉, 첫 모델의 목표는 "5거래일 뒤 상승 여부"를 예측하는 것이다.

이 방식은 과도한 가격 예측을 피하고, 반복 가능한 데이터 파이프라인과 모델 평가 구조를 만드는 데 집중하게 해준다.

## 12. Airflow 자동화 설계

Phase 2에서는 Airflow로 매일 일봉 수집을 자동화한다.

Airflow에서는 두 개의 DAG를 만든다.

```text
daily_kr_market_data_etl
  한국장 일봉 수집
  평일 16:10 Asia/Seoul 실행

daily_us_market_data_etl
  미국장 일봉 수집
  평일 17:30 America/New_York 실행
```

한국장과 미국장 DAG를 분리한 이유는 장 마감 시간이 다르기 때문이다. 한국장은 한국 시간 기준으로 장 마감 후 실행하고, 미국장은 뉴욕 시간 기준 장 마감 후 실행한다.

각 DAG는 다음 흐름을 실행한다.

```text
Airflow schedule
  -> local_market_data_etl 실행
  -> yfinance에서 최근 10일치 OHLCV 수집
  -> 기존 raw CSV 읽기
  -> date 기준 merge/dedup
  -> raw CSV 다시 저장
  -> 기본 피처 생성
  -> processed CSV 저장
  -> PostgreSQL metadata 기록
```

여기서 중요한 설계는 최근 10일치를 overlap으로 다시 가져오는 것이다.

하루치만 가져오면 장 마감 직후 데이터가 아직 반영되지 않았거나, 거래량/수정주가가 나중에 정정되었거나, 서버가 며칠 꺼져 있던 경우 누락이 생길 수 있다. 그래서 매일 최근 10일치를 다시 가져오고, 기존 데이터와 날짜 기준으로 병합한다.

중복 날짜는 새로 받은 데이터가 남도록 처리한다.

```text
기존 데이터
+ 새로 받은 최근 10일 데이터
-> date 기준 중복 제거
-> 같은 날짜는 새 데이터 유지
-> 전체 날짜순 정렬
```

이 방식으로 기존 백필 데이터를 보존하면서도 최근 데이터 정정과 누락을 흡수할 수 있다.

## 13. Airflow catchup 설계

Airflow DAG에는 `catchup=True`를 설정한다.

이 설정은 서버가 꺼져 있어 정해진 실행 시간을 놓쳤을 때 중요하다.

예를 들어 서버1이 꺼져 있어서 한국장 16:10 실행을 놓쳤다고 하자. 이후 서버1이 다시 켜지고 Airflow scheduler가 올라오면, Airflow는 놓친 schedule interval을 DAG run으로 생성한다. 그리고 해당 run을 실행하면서 최근 10일치 데이터를 다시 가져온다.

이 프로젝트에서는 서버1과 서버2가 홈서버 환경에 있고, 컴퓨터가 꺼질 수 있기 때문에 catchup이 필요하다.

또한 `max_active_runs=1`을 설정해 한 번에 여러 run이 동시에 몰리지 않게 했다. 서버가 오래 꺼져 있었다면 여러 catchup run이 생길 수 있는데, 이 경우에도 하나씩 순서대로 실행되게 하는 것이 안전하다.

## 14. Docker Compose 운영

Airflow는 Docker Compose로 실행한다.

구성 서비스는 다음과 같다.

```text
airflow-postgres
  Airflow 자체 메타데이터 DB

airflow-webserver
  Airflow UI 제공

airflow-scheduler
  DAG 스케줄링과 Task 실행 관리

airflow-init
  Airflow DB migration과 관리자 계정 생성을 위한 1회성 컨테이너
```

여기서 `airflow-postgres`는 ChartMaster 데이터 메타데이터 DB가 아니다. 이 PostgreSQL은 Airflow 자체가 DAG run, task instance, user, permission 등을 관리하기 위해 사용하는 내부 DB다.

ChartMaster의 데이터셋 메타데이터는 서버2 PostgreSQL에 저장된다.

즉 PostgreSQL이 두 종류다.

```text
Airflow 내부 PostgreSQL
  Airflow 운영용
  docker compose 안에서 실행

ChartMaster PostgreSQL
  데이터셋/파이프라인/모델 메타데이터용
  서버2에서 실행
```

컨테이너는 `restart: unless-stopped`로 설정했다.

따라서 서버1이 재부팅되면 Docker 서비스가 자동으로 시작되고, Airflow webserver, scheduler, postgres 컨테이너도 자동으로 올라온다. scheduler가 올라온 뒤 놓친 DAG run이 있으면 catchup으로 실행한다.

## 15. 실제 발생한 문제와 해결

### Docker 권한 문제

처음 Docker Compose를 실행할 때 다음 에러가 발생했다.

```text
permission denied while trying to connect to the Docker daemon socket
```

이 문제는 `docker-compose.yml` 파일이 없어서 발생한 것이 아니었다. Docker CLI는 설치되어 있었고, compose 파일도 존재했다. 문제는 현재 터미널 세션의 사용자가 Docker daemon socket에 접근할 권한이 없었다는 점이다.

Docker CLI는 `/var/run/docker.sock`이라는 Unix socket을 통해 Docker daemon과 통신한다. 이 socket은 보통 `root:docker` 소유이며, root 또는 docker 그룹 사용자만 접근할 수 있다.

시스템의 `/etc/group`에는 `dnhs01`이 docker 그룹에 등록되어 있었지만, 현재 로그인 세션에는 아직 docker 그룹이 반영되지 않았다. 리눅스에서는 그룹 변경이 기존 세션에 바로 적용되지 않기 때문이다.

임시 해결로 다음 방식으로 docker 그룹 권한을 가진 명령 세션을 열어 실행했다.

```bash
sg docker -c 'docker compose --env-file ../.env up -d --build'
```

정식 해결은 로그아웃 후 재로그인하거나, 현재 터미널에서 다음을 실행하는 것이다.

```bash
newgrp docker
```

그 후 `groups` 출력에 `docker`가 포함되어야 한다.

### Airflow 컨테이너 UID 문제

Airflow 컨테이너는 서버1의 SSH 키를 읽고 서버2에 접근해야 한다. 그래서 컨테이너를 서버1 사용자와 같은 UID인 `1000`으로 실행하도록 설정했다.

하지만 Airflow Docker 이미지 안에는 UID 1000에 해당하는 사용자 이름이 없었다. Airflow는 실행 사용자의 이름과 home directory가 필요하기 때문에 다음 에러가 발생했다.

```text
KeyError: getpwuid(): uid not found: 1000
AirflowConfigException:
The user that Airflow is running as has no username
```

해결 방법은 Dockerfile에서 컨테이너 내부에 `dnhs01` 사용자를 추가하는 것이었다.

```dockerfile
USER root
RUN useradd --uid 1000 --gid 0 --home-dir /home/dnhs01 --create-home --shell /bin/bash dnhs01

USER airflow
```

이렇게 해서 컨테이너 내부에서도 UID 1000이 `dnhs01`이라는 사용자로 인식되도록 했다.

### Airflow start_date 문제

DAG를 처음 만들었을 때 `start_date`를 현재 날짜로 잡았다. 하지만 Airflow에서 `start_date`는 "이 시간에 즉시 실행"이라는 의미가 아니라, schedule interval을 계산하는 기준점이다.

처음에는 DAG가 등록되었지만 바로 실행 이력이 생기지 않았다.

이를 해결하기 위해 `start_date`를 하루 전으로 조정했다.

```python
start_date=pendulum.datetime(2026, 7, 27, tz="Asia/Seoul")
```

그 결과 catchup run이 생성되었고, 한국장 DAG가 성공적으로 실행되었다.

## 16. 현재까지 구현 결과

현재까지 완료된 항목은 다음과 같다.

```text
서버2 파일 저장소 구조 생성
서버2 PostgreSQL chartmaster DB 구성
yfinance 기반 OHLCV 백필
raw/processed 데이터 저장
기본 피처 생성
PostgreSQL metadata 기록
WDC 추가 및 SNDK experimental 이동
Airflow Docker Compose 구성
한국장/미국장 DAG 분리
장마감 후 자동 수집 스케줄 설정
catchup 설정
최근 10일 overlap 수집
date 기준 merge/dedup
한국장 DAG 첫 자동 실행 성공
```

한국장 첫 자동 실행 결과는 다음과 같다.

```text
DAG: daily_kr_market_data_etl
상태: success
실행 시각: 2026-07-28 16:11 KST
수집 범위: 2026-07-17 ~ 2026-07-28
대상 종목:
  000660.KS
  005930.KS
  022100.KS
  005380.KS
최신 데이터 end_date: 2026-07-27
저장 위치:
  서버2 raw
  서버2 processed
  서버2 PostgreSQL metadata
```

## 17. 전체 파이프라인

현재 기준 전체 파이프라인은 다음과 같다.

```text
Airflow scheduler
  -> daily_kr_market_data_etl / daily_us_market_data_etl
  -> BashOperator
  -> Python ETL 실행
  -> assets.json 로드
  -> market 기준 자산 필터링
  -> yfinance OHLCV 수집
  -> 서버2 기존 raw CSV 읽기
  -> 최근 수집 데이터와 merge/dedup
  -> 서버2 raw CSV 저장
  -> 기본 피처 생성
  -> 서버2 processed CSV 저장
  -> 서버2 PostgreSQL에 pipeline_runs/datasets 기록
  -> Airflow task success/failure 기록
```

이 구조의 핵심은 Airflow가 실제 데이터를 직접 저장하는 것이 아니라, ETL 코드를 정해진 시간에 실행하고 로그/실패/재시도/스케줄을 관리한다는 점이다.

## 18. 향후 계획

다음 단계는 Phase별로 진행한다.

```text
Phase 1: 로컬 시장 데이터 기준선과 서버2 저장 구조
  과거 OHLCV 백필, 서버2 raw/processed 저장, PostgreSQL metadata, 기본 피처 생성

Phase 2: Airflow 로컬 자동화
  한국장/미국장 일봉 자동 수집, catchup, 10일 overlap merge, dedup, 서버2 metadata 기록

Phase 3: Electron Dashboard UI 설계와 Mock Prototype
  Dashboard, Assets, Asset Detail, Events, Airflow/Pipelines 화면 우선 구현
  Predictions, Reports, Settings는 mock 또는 placeholder로 시작

Phase 4: FastAPI 데이터 제공 계층과 서비스 경계 설계
  Electron mock JSON과 동일한 API response contract 정의
  mock provider와 live provider 분리
  Electron이 서버2 파일 저장소나 PostgreSQL에 직접 접근하지 않도록 서비스 경계 설정

Phase 5: 데이터 품질, 백필, 재처리 전략
  종목 유니버스와 데이터 소스 coverage 검증
  누락, 중복, 날짜 범위, row count 차이 확인
  백필 재실행과 실패 데이터 재처리 절차 정리

Phase 6: 운영 안정성과 백업/복구 설계
  서버2 파일 저장소 백업, PostgreSQL backup/restore, Airflow 장애 대응 runbook 작성
  재시작, 재실행, 로그 확인, 복구 테스트 절차 정리

Phase 7: 머신러닝 모델 학습 파이프라인
  baseline 모델, time series split, leakage 방지, metric, model artifact 기록
  이후 Airflow 기반 재학습으로 확장 가능한 구조 설계

Phase 8: RAG와 외부 요인 분석 계층
  뉴스/리포트/매크로 문서 수집, RAG 요약, 감성/event feature 생성
  급등/급락 이벤트 화면과 AI 리포트 흐름에 연결

Phase 9: 로컬 운영 구조를 AWS로 이전
  서버2 파일 저장소와 PostgreSQL 구조를 S3/RDS로 이전
  IAM, security group, storage provider 전환, 비용 관리 기준 정리

Phase 10: SageMaker와 운영 관찰성
  Airflow에서 SageMaker Training Job 실행, CloudWatch/logging/backup 확인
  로컬 Airflow 운영과 AWS managed training 운영 경험 비교
```

## 19. 포트폴리오에서 설명할 수 있는 문장

이 프로젝트는 다음과 같이 설명할 수 있다.

```text
ChartMaster는 주식 시장 데이터를 이용해 데이터 수집, 저장소 설계, Airflow 자동화, PostgreSQL 메타데이터 관리, 백업/복구, AWS 전환, 모델 학습, AI/RAG 분석을 단계적으로 학습하기 위한 Data Engineering/MLOps 포트폴리오 프로젝트입니다.
```

조금 더 기술적으로 설명하면 다음과 같다.

```text
서버1에서 Airflow와 ETL 코드를 실행하고, 서버2를 파일 저장소와 PostgreSQL 메타데이터 DB로 분리했습니다. yfinance로 한국장/미국장 일봉 데이터를 수집하고, raw/processed 데이터를 분리 저장하며, pipeline_runs와 datasets 테이블에 실행 이력과 데이터셋 위치를 기록했습니다. Airflow DAG는 한국장과 미국장의 장마감 시간을 고려해 분리했고, 서버가 꺼져 있던 경우에도 catchup과 10일 overlap merge를 통해 누락을 보완하도록 설계했습니다.
```

면접에서 장애 해결 경험으로는 다음을 설명할 수 있다.

```text
Docker daemon socket 권한 문제, Airflow 컨테이너 UID 문제, Airflow start_date/catchup 동작 문제를 직접 확인하고 해결했습니다. 단순히 DAG를 작성한 것이 아니라, 로컬 운영 환경에서 실제로 자동 실행되도록 Docker Compose, restart policy, Airflow metadata DB, scheduler, webserver 상태까지 확인했습니다.
```

## 20. 현재 상태 요약

현재 ChartMaster는 Phase 1, Phase 3, Phase 5를 완료했고, Phase 2 자동 수집을 운영하고 있다. Phase 4의 핵심 FastAPI 조회 계층도 구현했다. 다음 단계에서는 운영 안정성과 백업/복구 절차를 정리한 뒤 모델 학습 파이프라인으로 넘어간다.

```text
Phase 1: 완료
  yfinance 백필
  서버2 저장소
  PostgreSQL metadata
  기본 피처 생성

Phase 2: 운영 중
  Airflow Docker Compose 실행
  한국장/미국장 DAG 자동 실행 성공
  서버 재시작 후 자동 실행 확인
  catchup, 10일 overlap merge, dedup 구조 적용
  실패/retry 강제 검증은 별도 운영 테스트로 남김

Phase 3: 완료
  Electron Dashboard와 종목별 대화형 차트 구현
  Mock/Live Provider 계약과 데이터 검증 상세 화면 확정

Phase 4: 핵심 연결 구현
  Server 1 FastAPI에서 Server 2 실데이터와 품질 리포트 조회

Phase 5: 완료
  데이터 품질 검사, 거래소 캘린더, curated 계층, 재처리, Airflow 품질 Gate 구현
  최신 품질 검사 29종목 PASS, 오류 0, 경고 12
  KRX 인증 기반 독립 원천 검증은 후속 보강 항목으로 분리
```

다음으로는 AWS나 모델링으로 바로 넘어가지 않고 Phase 6에서 백업, 복구, 장애 대응, 운영 점검 절차를 먼저 정리한다. Electron 화면과 핵심 API 계약이 마련됐으므로 이후 품질 Gate, 모델 결과와 RAG 리포트를 연결할 표시 위치도 명확해졌다.
