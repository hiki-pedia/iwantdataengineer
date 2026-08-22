# ChartMaster 장애 대응 실험 기록

## 목적

이 문서는 Phase 6에서 수행하는 장애 대응 실험을 기록한다. 장애 실험은 실제 데이터를 손상시킬 수 있으므로 낮은 위험부터 진행한다.

## 실험 원칙

- 운영 데이터를 삭제하지 않는다.
- 먼저 정상 상태 기준을 기록한다.
- 실험 전 백업 파일과 PostgreSQL dump가 있는지 확인한다.
- 컨테이너 중단 실험은 `restart: unless-stopped` 동작을 확인하는 범위에서만 수행한다.
- PostgreSQL 중단, 네트워크 차단, SSH 실패 실험은 백업/복구 절차가 확인된 뒤 진행한다.

## 완료한 검증

### 1. FastAPI health check

명령:

```bash
curl -sf http://127.0.0.1:8000/health
```

결과:

```text
status=ok
storage=SshObjectStorage
assetCount=29
```

판정:

```text
PASS
```

### 2. Server 2 SSH 접근

명령:

```bash
ssh -o BatchMode=yes dnhs02@192.168.0.9 hostname
```

결과:

```text
dnhs02-System-Product-Name
```

판정:

```text
PASS
```

### 3. 파일 저장소 백업 무결성

백업:

```text
backups/files/chartmaster_files_20260823_005448.tar.gz
```

검증:

```bash
tar -tzf backups/files/chartmaster_files_20260823_005448.tar.gz
```

판정:

```text
PASS
```

### 4. PostgreSQL metadata 복구 테스트

백업:

```text
backups/postgres/chartmaster_metadata_20260823_005533_server2.sql.gz
```

검증:

```text
임시 DB 생성
psql -v ON_ERROR_STOP=1 restore
public schema table count = 6
임시 DB 삭제
```

판정:

```text
PASS
```

### 5. FastAPI 컨테이너 재시작

명령:

```bash
docker restart chartmaster-chartmaster-api-1
curl -sf http://127.0.0.1:8000/health
```

결과:

```text
health response: {"status":"ok","storage":"SshObjectStorage","assetCount":29}
docker health: healthy
```

판정:

```text
PASS
```

의미:

```text
FastAPI 컨테이너 단독 재시작 후 Server 2 SSH 저장소를 다시 읽을 수 있고, Docker healthcheck도 정상으로 복귀했다.
```

### 6. Airflow webserver 재시작

명령:

```bash
docker restart chartmaster-airflow-webserver-1
curl -sf http://127.0.0.1:8081/health

cd /home/dnhs01/iwantdataengineer/chartmaster
docker compose --env-file ../.env exec -T airflow-scheduler \
  airflow dags list | rg 'daily_(kr|us)_market_data_etl|dag_id'
```

결과:

```text
docker health: healthy
airflow /health: ok
daily_kr_market_data_etl loaded, is_paused=False
daily_us_market_data_etl loaded, is_paused=False
```

판정:

```text
PASS
```

의미:

```text
Airflow webserver 재시작은 UI/API 계층 재기동이며 scheduler와 DAG 이력은 유지된다.
```

### 7. Airflow scheduler 재시작

명령:

```bash
docker restart chartmaster-airflow-scheduler-1

cd /home/dnhs01/iwantdataengineer/chartmaster
docker compose --env-file ../.env exec -T airflow-scheduler \
  airflow jobs check --job-type SchedulerJob

docker compose --env-file ../.env exec -T airflow-scheduler \
  airflow dags list-runs -d daily_kr_market_data_etl --no-backfill -o table | head

docker compose --env-file ../.env exec -T airflow-scheduler \
  airflow dags list-runs -d daily_us_market_data_etl --no-backfill -o table | head
```

결과:

```text
SchedulerJob: Found one alive job.
daily_kr_market_data_etl recent runs visible
daily_us_market_data_etl recent runs visible
```

판정:

```text
PASS
```

의미:

```text
스케줄러 단독 재시작 후 Airflow metadata DB의 DAG run 이력을 계속 조회할 수 있고 scheduler job도 정상으로 확인된다.
```

### 8. 품질 검사 실패 유도

운영 데이터와 최신 품질 리포트를 손상시키지 않기 위해 임시 빈 로컬 저장소와 `--no-write-report`를 사용했다.

명령:

```bash
tmpdir=$(mktemp -d)

CHARTMASTER_DATA_DIR="$tmpdir" \
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=chartmaster/src \
chartmaster/.venv/bin/python -m chartmaster.pipelines.local_market_data_quality \
  --symbols 005930.KS \
  --as-of 2026-08-23 \
  --local-only \
  --no-write-report
```

결과:

```text
005930.KS: FAIL raw_rows=0 feature_rows=0 range=None..None
  ERROR missing_raw_dataset: No such file or directory
Summary: assets=1 passed=0 failed=1 errors=1 warnings=0
Report: disabled
exit_status=1
```

판정:

```text
PASS
```

의미:

```text
품질 검사에서 error-level 문제가 발생하면 프로세스가 non-zero exit code로 종료된다. Airflow BashOperator에서는 이 상태가 Task 실패로 기록된다.
```

## 아직 진행하지 않은 장애 실험

다음 실험은 이후 순서대로 진행한다.

| 우선순위 | 실험 | 위험도 | 확인할 것 |
| --- | --- | --- | --- |
| 1 | Server 2 SSH 실패 시뮬레이션 | 중간 | ETL 실패 로그와 retry |
| 2 | PostgreSQL 중단/복구 | 높음 | metadata 기록 실패와 복구 절차 |

## 다음 실험 후보

다음 단계에서는 Server 2 SSH 실패 시뮬레이션을 수행한다.

확인 순서:

```text
잘못된 Server 2 host/user/env로 수동 ETL 실행
  -> SSH 실패 로그 확인
  -> non-zero exit 확인
  -> 실제 env로 정상 복구 확인
```

이 실험은 운영 SSH 설정을 변경하지 않고, 임시 환경변수로 실패를 유도한다.
