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
`Found one alive job`은 scheduler 재시작 후 Airflow SchedulerJob이 다시 살아났다는 뜻이다.
한국장/미국장 DAG run 이력 조회 성공은 scheduler 재시작 뒤에도 Airflow metadata DB의 실행 이력이 유지된다는 뜻이다.
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

### 9. Server 2 SSH 실패 시뮬레이션

운영 SSH 설정을 변경하지 않고, 명령 실행 시점에만 불통 테스트 주소를 환경변수로 넣어 실패를 유도했다. 최신 품질 리포트를 덮어쓰지 않기 위해 `--no-write-report`를 사용했다.

명령:

```bash
CHARTMASTER_SERVER2_HOST=192.0.2.1 \
CHARTMASTER_SERVER2_USER=dnhs02 \
CHARTMASTER_SERVER2_PORT=22 \
CHARTMASTER_SERVER2_IDENTITY_FILE=/home/dnhs01/.ssh/id_ed25519 \
CHARTMASTER_SERVER2_DATA_DIR=/home/dnhs02/iwantdataengineer/chartmaster \
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=chartmaster/src \
chartmaster/.venv/bin/python -m chartmaster.pipelines.local_market_data_quality \
  --symbols 005930.KS \
  --as-of 2026-08-23 \
  --no-write-report
```

결과:

```text
005930.KS: FAIL raw_rows=0 feature_rows=0 range=None..None
  ERROR missing_raw_dataset: ssh ... dnhs02@192.0.2.1 ... returned non-zero exit status 255
Summary: assets=1 passed=0 failed=1 errors=1 warnings=0
Report: disabled
exit_status=1
```

판정:

```text
PASS
```

복구 확인:

```text
FastAPI /health 정상
실제 Server 2 설정으로 005930.KS 품질 검사 PASS
컨테이너 상태 정상
```

의미:

```text
Server 2 SSH 접근 실패는 품질 검사 error로 감지되고 non-zero exit code로 종료된다.
Airflow BashOperator에서는 이 상태가 Task 실패로 기록되며, retry 정책의 대상이 된다.
```

## 보류한 장애 실험

다음 실험은 Phase 6 완료 조건에서는 제외하고 후속 운영 고도화 항목으로 보류한다.

| 우선순위 | 실험 | 위험도 | 확인할 것 |
| --- | --- | --- | --- |
| 보류 | PostgreSQL 중단/복구 | 높음 | metadata 기록 실패와 복구 절차 |

보류 이유:

```text
현재 Phase 6에서는 백업/복구 검증, 컨테이너 재시작, 품질 실패, SSH 실패까지 확인했다.
PostgreSQL 컨테이너 중단은 실제 metadata 기록과 다음 수집 실행에 영향을 줄 수 있어 지금 굳이 건드릴 이득이 작다.
대신 추후 별도 점검 시간에 수행한다.
```

## Phase 6 판정

```text
Phase 6 완료
```

완료 기준:

- 정상 상태 기준 문서화
- 파일 저장소 백업 생성 및 tar 검증
- PostgreSQL metadata dump 생성 및 임시 DB restore 검증
- FastAPI 재시작 실험
- Airflow webserver 재시작 실험
- Airflow scheduler 재시작 실험
- 품질 검사 실패 유도
- Server 2 SSH 실패 시뮬레이션
- PostgreSQL 중단 실험은 후속 보류로 명시
