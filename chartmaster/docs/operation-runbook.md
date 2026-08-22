# ChartMaster 운영 점검 Runbook

## 목적

이 문서는 ChartMaster Phase 6에서 서버1/서버2 기반 데이터 플랫폼의 정상 상태를 정의하고, 매일 또는 장애 발생 시 어떤 순서로 확인할지 정리한다.

ChartMaster는 현재 다음 경계로 운영한다.

```text
Server 1
  Airflow webserver/scheduler
  FastAPI
  Electron web preview

Server 2
  ChartMaster file storage
  ChartMaster PostgreSQL metadata DB
```

## 현재 정상 상태 기준

Server 1 Docker 컨테이너:

```bash
docker ps --format '{{.Names}} {{.Status}} {{.Ports}}'
```

정상 기준:

```text
chartmaster-airflow-webserver-1   Up, healthy, 8081->8080
chartmaster-airflow-scheduler-1   Up
chartmaster-airflow-postgres-1    Up, healthy
chartmaster-chartmaster-api-1     Up, healthy, 8000->8000
chartmaster-web-preview           Up, 5173->80
```

FastAPI health:

```bash
curl -sf http://127.0.0.1:8000/health
```

정상 기준:

```json
{"status":"ok","storage":"SshObjectStorage","assetCount":29}
```

Airflow DAG 로드 상태:

```bash
cd /home/dnhs01/iwantdataengineer/chartmaster
docker compose --env-file ../.env exec -T airflow-scheduler \
  airflow dags list | rg 'daily_(kr|us)_market_data_etl|dag_id'
```

정상 기준:

- `daily_kr_market_data_etl` 로드
- `daily_us_market_data_etl` 로드
- `is_paused=False`

Server 2 접근:

```bash
ssh -o BatchMode=yes dnhs02@192.168.0.9 hostname
```

정상 기준:

```text
dnhs02-System-Product-Name
```

Server 2 데이터 저장소:

```bash
ssh dnhs02@192.168.0.9 \
  'cd /home/dnhs02/iwantdataengineer/chartmaster && du -sh raw curated processed reports backups'
```

## 매일 확인할 항목

1. Airflow UI에서 한국장/미국장 DAG 최근 실행이 success인지 확인한다.
2. FastAPI `/health`가 정상인지 확인한다.
3. Electron 또는 API에서 최신 데이터 날짜가 예상 장마감 이후 날짜인지 확인한다.
4. 품질 리포트의 error count가 0인지 확인한다.
5. warning count가 급증하지 않았는지 확인한다.

품질 리포트 수동 확인:

```bash
cd /home/dnhs01/iwantdataengineer
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=chartmaster/src \
chartmaster/.venv/bin/python -m chartmaster.pipelines.local_market_data_quality \
  --tier all \
  --as-of YYYY-MM-DD \
  --no-write-report
```

현재 정상 기준:

```text
assets=29 passed=29 failed=0 errors=0 warnings=1
```

남은 warning은 SK하이닉스의 과거 `adjusted_close <= 0` 778행이다. `2007-03-02`는 임시공휴일로 확인되어 한국장 캘린더 예외에 반영했다.

## 매주 확인할 항목

1. Server 2 백업 파일이 생성되는지 확인한다.
2. PostgreSQL dump를 임시 DB에 복원해본다.
3. Server 2 디스크 사용량을 확인한다.
4. Airflow 실패 DAG run이 남아 있는지 확인한다.
5. 오래된 로그와 백업 보관 정책을 점검한다.

디스크 사용량:

```bash
ssh dnhs02@192.168.0.9 'df -h /home/dnhs02 && du -sh /home/dnhs02/iwantdataengineer/chartmaster/*'
```

최근 DAG run:

```bash
cd /home/dnhs01/iwantdataengineer/chartmaster
docker compose --env-file ../.env exec -T airflow-scheduler \
  airflow dags list-runs -d daily_kr_market_data_etl --no-backfill -o table | head -n 10

docker compose --env-file ../.env exec -T airflow-scheduler \
  airflow dags list-runs -d daily_us_market_data_etl --no-backfill -o table | head -n 10
```

## 장애 발생 시 기본 순서

1. 문제가 UI인지 API인지 Airflow인지 Server 2인지 분리한다.
2. FastAPI `/health`를 확인한다.
3. Docker 컨테이너 상태를 확인한다.
4. Airflow DAG run과 task log를 확인한다.
5. Server 2 SSH 접근을 확인한다.
6. Server 2 PostgreSQL 컨테이너 상태를 확인한다.
7. 최근 백업 파일과 품질 리포트를 확인한다.

Server 2 DB 컨테이너 확인:

```bash
ssh dnhs02@192.168.0.9 'docker ps --format "{{.Names}} {{.Status}}" | rg chartmaster-postgres'
```

## 현재 확인 결과

2026-08-23 기준:

- Server 1 Airflow webserver: healthy
- Server 1 FastAPI: healthy
- Server 1 Airflow scheduler: running
- Server 2 SSH: reachable
- Server 2 PostgreSQL container: running
- 품질 검사: 29 assets PASS, errors 0, warnings 1
- 파일 저장소 백업: 생성 및 tar 목록 확인 완료
- PostgreSQL dump: 생성 및 임시 DB restore 확인 완료
