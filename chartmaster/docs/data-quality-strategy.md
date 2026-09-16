# 시장 데이터 품질 전략

## 품질 기준

`local_market_data_quality`는 서버2의 raw와 processed 파일을 읽어 다음 항목을 검사한다.

| 구분 | 검사 | 판정 |
|---|---|---|
| 구조 | 필수 컬럼, 빈 데이터 | 오류 |
| 날짜 | 파싱 실패, 중복, 정렬, 미래 날짜 | 오류 |
| 최신성 | 거래소 캘린더의 최신 세션이 없음 | 오류 |
| OHLCV | 결측·비수치, 0 이하 OHLC, 음수 거래량 | 오류 |
| 공급자 이상 | 0 이하 보정주가, OHLC high/low 모순 | 경고 |
| Coverage | 거래소 예정 세션이 데이터에 없음 | 경고 |
| 피처 | 필수 컬럼, 중복 날짜, 무한대 | 오류 |
| 계층 일치 | raw/feature 행 수와 날짜 집합 | 오류 |

한국장은 XKRX, 미국장은 XNYS 거래 캘린더로 예정 세션을 계산한다. 주말과 정상 휴장은 누락으로 보지 않는다. 캘린더에 반영되지 않은 한국장 임시 휴장일은 명시적인 예외로 관리한다. 현재 예외에는 확인된 `2007-03-02` 임시공휴일과 2026년 한국 휴장일이 포함된다. XNYS의 오래된 휴일 정의에서 오탐이 확인돼 미국 세션 누락 검사는 1970년 이후에 적용하고, OHLCV 구조 검사는 전체 이력에 그대로 적용한다.

공급자별 보정 방식처럼 자동으로 오류라고 단정할 수 없는 항목은 경고로 분리한다. Yahoo 원천의 이상은 raw에 보존하고, 확인된 교정값은 curated에 기록한다.

## 결과 저장

품질 리포트는 서버2 파일 저장소 아래에 저장한다.

```text
reports/data_quality/market=KR/latest.json
reports/data_quality/market=KR/history/quality_<실행시각>.json
reports/data_quality/market=US/latest.json
reports/data_quality/market=US/history/quality_<실행시각>.json
```

`latest.json`은 화면과 운영 점검에서 사용하고, `history`는 품질 변화 추적에 사용한다. raw와 processed 파일은 품질 검사 과정에서 수정하지 않는다.

## Airflow 품질 Gate

각 시장 DAG는 다음 순서로 실행한다.

```text
KR: collect_kr_daily_ohlcv -> curate_kr_market_data -> validate_kr_market_data
US: collect_us_daily_ohlcv -> validate_us_market_data
```

오류가 하나라도 있으면 품질 Task가 종료 코드 1을 반환해 DAG 실행이 실패한다. 경고만 있으면 DAG는 성공하며 리포트에 경고 내역이 남는다.

## 수동 실행

쓰기 없이 전체 데이터를 검사한다.

```bash
cd /home/dnhs01/iwantdataengineer/chartmaster
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python \
  -m chartmaster.pipelines.local_market_data_quality \
  --tier all \
  --no-write-report
```

한국장만 검사하고 리포트를 저장한다.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python \
  -m chartmaster.pipelines.local_market_data_quality \
  --market KR \
  --tier all
```
