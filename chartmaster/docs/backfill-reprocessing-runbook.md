# 백필과 재처리 Runbook

## 구분

- 백필: 공급자에서 지정 기간을 다시 내려받아 기존 raw와 날짜 기준으로 병합한다.
- 재처리: 저장된 raw를 다시 읽어 최신 피처 코드로 processed 파일을 재생성한다.
- 재수집: 최근 구간의 정정·누락 가능성 때문에 정기 DAG가 10일을 겹쳐 받는 작업이다.

## 1. 문제 확인

먼저 데이터를 변경하지 않는 품질 검사를 실행한다.

```bash
cd /home/dnhs01/iwantdataengineer/chartmaster
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python \
  -m chartmaster.pipelines.local_market_data_quality \
  --symbols 005930.KS \
  --no-write-report
```

Airflow 로그, 서버2 raw 파일, processed 파일, PostgreSQL `pipeline_runs`와 `datasets`를 함께 확인해 수집 실패인지 변환 실패인지 구분한다.

## 2. 기간 백필

`--end`는 yfinance에서 제외되는 날짜이므로 필요한 마지막 거래일의 다음 날짜를 지정한다.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python \
  -m chartmaster.pipelines.local_market_data_etl \
  --symbols 005930.KS \
  --start 2026-08-01 \
  --end 2026-08-22
```

기본 모드는 기존 데이터와 병합하고 날짜가 겹치면 새로 받은 행을 유지한다. 같은 명령을 반복해도 날짜 중복이 늘어나지 않는다. `--replace-existing`은 전체 이력을 대체하므로 공급자 범위를 확인하지 않은 상태에서는 사용하지 않는다.

## 3. 피처 재처리

먼저 dry-run으로 대상과 행 수를 확인한다.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python \
  -m chartmaster.pipelines.local_market_data_reprocess \
  --market KR \
  --tier all
```

확인 후에만 `--write`를 붙인다.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python \
  -m chartmaster.pipelines.local_market_data_reprocess \
  --market KR \
  --tier all \
  --write
```

이 명령은 raw 파일을 수정하지 않고 processed feature만 다시 쓴다. 쓰기 모드에서는 PostgreSQL에 재처리 실행과 데이터셋 메타데이터를 기록한다.

## 4. 한국장 교차 검증과 Curated 재생성

Yahoo 원천의 OHLC 모순과 예정 거래일 누락을 pykrx_naver로 교차 확인한다.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python \
  -m chartmaster.pipelines.local_kr_market_data_curate \
  --tier all
```

보조 공급자 응답은 `raw/market_data/provider=pykrx_naver`에 별도로 저장한다. Yahoo raw는 변경하지 않는다. 교체·보완된 결과는 `curated/market_data`에 저장하고 processed feature를 curated 기준으로 다시 생성한다.

## 5. 사후 검증

같은 심볼 또는 시장을 다시 품질 검사한다. 행 수, 날짜 범위, 중복, 무한대 피처, raw/feature 날짜 일치가 통과해야 작업을 종료한다.

## 재처리 판단 기준

- 수집 코드 또는 공급자 심볼 변경: 백필
- 특정 날짜 누락 또는 공급자 가격 정정: 해당 기간 백필
- 피처 계산식 변경: raw는 유지하고 피처 재처리
- raw 스키마 변경: 별도 마이그레이션 계획 수립 후 백필과 재처리
- 공급자 이상 행 발견: 원본 유지, 다른 소스 교차 검증 후 curated 계층 생성
