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

## 아직 진행하지 않은 장애 실험

다음 실험은 이후 순서대로 진행한다.

| 우선순위 | 실험 | 위험도 | 확인할 것 |
| --- | --- | --- | --- |
| 1 | Airflow webserver 재시작 | 낮음 | UI 복구와 DAG 상태 유지 |
| 2 | Airflow scheduler 재시작 | 중간 | 스케줄러 재기동 후 DAG 실행 유지 |
| 3 | 품질 검사 실패 유도 | 중간 | error 발생 시 Task 실패 |
| 4 | Server 2 SSH 실패 시뮬레이션 | 중간 | ETL 실패 로그와 retry |
| 5 | PostgreSQL 중단/복구 | 높음 | metadata 기록 실패와 복구 절차 |

## 다음 실험 후보

다음 단계에서는 Airflow webserver 재시작을 수행한다.

확인 순서:

```text
docker restart chartmaster-airflow-webserver-1
  -> docker ps health 확인
  -> Airflow UI 접속 확인
  -> DAG 목록 확인
```

이 실험은 Airflow webserver만 재시작하며 scheduler와 Server 2 데이터는 변경하지 않는다.
