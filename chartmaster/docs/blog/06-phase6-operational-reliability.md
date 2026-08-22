# Phase 6 - 운영 안정성, 백업, 복구 설계

## 이번 Phase의 목적

Phase 6의 목적은 ChartMaster를 단순히 실행되는 데이터 프로젝트가 아니라 운영 가능한 데이터 플랫폼으로 다루는 것이다.

Phase 1~5에서는 데이터를 수집하고, Airflow로 자동화하고, 품질 검사와 curated 계층까지 만들었다. 하지만 실제 운영에서는 다음 질문이 남는다.

- 서버가 재부팅되면 서비스가 다시 올라오는가?
- 데이터 파일과 metadata DB를 백업하고 복구할 수 있는가?
- Airflow DAG가 실패했을 때 어디서 로그를 확인하는가?
- API가 죽었을 때 데이터가 문제인지 서버가 문제인지 분리할 수 있는가?
- 백업 파일이 실제로 복원 가능한지 확인했는가?

이번 Phase에서는 이 질문에 답하기 위해 정상 상태 기준, 백업 대상, 복구 절차, 장애 대응 실험 순서를 정리했다.

## 현재 운영 구조

ChartMaster는 두 대의 서버를 역할별로 나누어 운영한다.

```text
Server 1
  Airflow webserver
  Airflow scheduler
  FastAPI
  Electron web preview

Server 2
  chartmaster file storage
  chartmaster PostgreSQL metadata DB
```

Server 1은 실행 계층이고 Server 2는 데이터 계층이다. 이 구분은 이후 AWS로 이전할 때도 그대로 이어진다.

```text
Server 2 file storage -> S3
Server 2 PostgreSQL   -> RDS
Container healthcheck -> ECS/ALB healthcheck
Local logs            -> CloudWatch Logs
```

## 정상 상태를 먼저 정의하기

장애 대응을 하려면 먼저 정상 상태를 알아야 한다. 현재 정상 기준은 다음과 같다.

```text
Airflow webserver  Up, healthy, 8081
Airflow scheduler  Up
Airflow postgres   Up, healthy
FastAPI            Up, healthy, 8000
Web preview        Up, 5173
Server 2 SSH       reachable
Quality check      29 assets PASS, errors 0, warnings 1
```

FastAPI health check는 다음 응답을 기준으로 한다.

```json
{"status":"ok","storage":"SshObjectStorage","assetCount":29}
```

품질 경고 1건은 SK하이닉스의 오래된 보정주가 문제다. `2007-03-02`는 임시공휴일로 확인되어 한국장 캘린더 예외에 반영했고 더 이상 누락으로 보지 않는다.

## 백업 대상을 분리하기

백업 대상은 크게 파일 저장소와 PostgreSQL metadata DB로 나눴다.

파일 저장소:

```text
raw
curated
processed
reports
```

PostgreSQL metadata:

```text
pipeline_runs
datasets
data_quality_issues
model_versions
model_metrics
```

반대로 `.venv`, `node_modules`, `.vite`, `desktop/dist`, `__pycache__` 같은 재생성 가능한 파일은 백업 대상에서 제외했다.

## 파일 저장소 백업

Server 2에서 tar 백업을 만들고 SHA256 manifest를 남겼다.

```bash
tar -czf backups/files/chartmaster_files_${ts}.tar.gz \
  raw curated processed reports

sha256sum backups/files/chartmaster_files_${ts}.tar.gz \
  > backups/manifests/chartmaster_files_${ts}.sha256
```

1차 검증 결과:

```text
backup: backups/files/chartmaster_files_20260823_005448.tar.gz
size: 30M
검증: tar 목록 확인 완료
```

여기서 중요한 것은 백업 명령만 적은 것이 아니라 실제 파일을 열어 목록을 확인했다는 점이다.

## PostgreSQL 백업과 복구 테스트

처음에는 Server 1의 Airflow 컨테이너에 있는 `pg_dump`로 dump를 만들었다. 하지만 복원 중 `transaction_timeout` 설정 경고가 발생했다. 원인은 PostgreSQL 클라이언트와 서버 버전 차이였다.

그래서 백업 기준을 Server 2의 `chartmaster-postgres` 컨테이너 안에 있는 `pg_dump`로 바꿨다. 서버와 같은 버전의 클라이언트를 쓰면 restore 경고를 피할 수 있다.

```bash
docker exec chartmaster-postgres \
  pg_dump -U chartmaster chartmaster \
  | gzip > backups/postgres/chartmaster_metadata_${ts}_server2.sql.gz
```

복구 검증은 운영 DB를 덮어쓰지 않고 임시 DB에 수행했다.

```text
임시 DB 생성
dump restore with ON_ERROR_STOP=1
public schema table count 확인
임시 DB 삭제
```

1차 검증 결과:

```text
backup: backups/postgres/chartmaster_metadata_20260823_005533_server2.sql.gz
size: 30K
restore: success
restored_tables: 6
temporary database: dropped
```

이로써 Phase 6의 첫 번째 기준인 “백업 파일이 복구 가능한가?”를 통과했다.

## 장애 실험은 낮은 위험부터

아직 모든 장애 실험을 실행하지는 않았다. 먼저 낮은 위험 실험인 FastAPI 컨테이너 재시작, Airflow webserver 재시작, Airflow scheduler 재시작, 품질 검사 실패 유도를 수행했다.

FastAPI 재시작 실험:

```text
docker restart chartmaster-chartmaster-api-1
  -> /health 정상 응답
  -> Docker health 상태 healthy 복귀
```

Airflow webserver 재시작 실험:

```text
docker restart chartmaster-airflow-webserver-1
  -> /health 정상 응답
  -> Docker health 상태 healthy 복귀
  -> DAG 목록 조회 성공
```

Airflow scheduler 재시작 실험:

```text
docker restart chartmaster-airflow-scheduler-1
  -> SchedulerJob alive 확인
  -> 한국장/미국장 DAG run 이력 조회 성공
```

품질 실패 실험:

```text
임시 빈 로컬 저장소 + --no-write-report
  -> missing_raw_dataset error
  -> exit status 1
  -> 운영 품질 리포트 미변경
```

| 순서 | 실험 | 목적 |
| --- | --- | --- |
| 완료 | FastAPI 컨테이너 재시작 | healthcheck와 자동 복구 확인 |
| 완료 | Airflow webserver 재시작 | UI 복구와 DAG 상태 유지 확인 |
| 완료 | Airflow scheduler 재시작 | 스케줄러 job 복구 확인 |
| 완료 | 품질 검사 실패 유도 | error 발생 시 non-zero exit 확인 |
| 1 | Server 2 SSH 실패 시뮬레이션 | retry와 실패 로그 확인 |
| 2 | PostgreSQL 중단/복구 | metadata 기록 실패와 복구 절차 확인 |

운영 안정성 실험은 과감하게 하는 것보다 순서를 정하는 것이 중요하다. 특히 PostgreSQL 중단이나 SSH 차단은 실제 수집 작업에 영향을 줄 수 있으므로 백업과 복구 검증이 끝난 뒤 진행한다.

## 이번 Phase에서 배운 점

첫 번째는 백업과 복구는 다르다는 점이다. 백업 파일이 존재해도 실제 복원이 실패하면 운영 관점에서는 백업이 아니다.

두 번째는 도구 버전도 운영 리스크라는 점이다. Server 1의 `pg_dump`와 Server 2의 PostgreSQL 서버 버전이 다르면 restore 경고가 생길 수 있다. 그래서 DB 백업은 Server 2 DB 컨테이너와 같은 버전의 클라이언트로 수행하는 기준을 세웠다.

세 번째는 정상 상태 기준을 먼저 문서화해야 장애를 판단할 수 있다는 점이다. “안 된다”는 말만으로는 API 문제인지, Airflow 문제인지, Server 2 저장소 문제인지 알 수 없다.

## 현재까지의 Phase 6 결과

```text
운영 정상 상태 기준 정의
Server 1/Server 2 점검 명령 정리
파일 저장소 백업 생성 및 tar 검증
PostgreSQL dump 생성 및 임시 DB restore 검증
장애 실험 우선순위 정의
FastAPI 컨테이너 재시작 실험 PASS
Airflow webserver 재시작 실험 PASS
Airflow scheduler 재시작 실험 PASS
품질 검사 실패 유도 PASS
운영 점검 runbook 작성
백업/복구 runbook 작성
```

## 포트폴리오 설명 문장

홈서버 기반 데이터 플랫폼에서 Airflow, FastAPI, PostgreSQL, SSH 파일 저장소의 정상 상태 기준을 정의하고 운영 점검 runbook을 작성했습니다. Server 2의 raw/curated/processed/reports 파일 저장소를 tar와 SHA256 manifest로 백업하고, ChartMaster metadata PostgreSQL은 동일 버전의 DB 컨테이너 `pg_dump`로 백업하도록 구성했습니다. 생성한 dump는 운영 DB를 덮어쓰지 않고 임시 DB에 복원해 `ON_ERROR_STOP=1` 기준으로 검증했으며, 이를 통해 백업 파일 생성이 아니라 실제 복구 가능성까지 확인했습니다.
