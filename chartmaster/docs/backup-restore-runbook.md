# ChartMaster 백업/복구 Runbook

## 목적

Phase 6의 목표는 백업 파일을 만드는 데서 끝나지 않고, 실제로 복구 가능한지 확인하는 것이다.

ChartMaster의 백업 대상은 두 종류다.

```text
File storage backup
  raw
  curated
  processed
  reports

PostgreSQL metadata backup
  pipeline_runs
  datasets
  data_quality_issues
  model_versions
  model_metrics
```

Airflow metadata DB는 Airflow 내부 실행 상태를 위한 별도 DB다. ChartMaster 데이터셋 metadata DB와 목적이 다르므로 백업 정책도 분리한다.

## 백업 제외 대상

다음 항목은 재생성 가능하거나 프로젝트 산출물이 아니므로 정기 백업 대상에서 제외한다.

- `.venv`
- `node_modules`
- `.vite`
- `desktop/dist`
- `__pycache__`
- `.pytest_cache`
- Airflow 임시 로그 전체

Airflow 로그는 장애 분석에 필요하지만 장기 보관 대상은 별도 정책으로 분리한다.

## 파일 저장소 백업

Server 2에서 실행한다.

```bash
ts=$(date +%Y%m%d_%H%M%S)

cd /home/dnhs02/iwantdataengineer/chartmaster
mkdir -p backups/files backups/manifests

tar -czf backups/files/chartmaster_files_${ts}.tar.gz \
  raw curated processed reports

sha256sum backups/files/chartmaster_files_${ts}.tar.gz \
  > backups/manifests/chartmaster_files_${ts}.sha256
```

검증:

```bash
tar -tzf backups/files/chartmaster_files_${ts}.tar.gz | head
sha256sum -c backups/manifests/chartmaster_files_${ts}.sha256
```

## PostgreSQL metadata 백업

Server 2의 PostgreSQL 컨테이너와 같은 버전의 `pg_dump`를 사용한다. Server 1 또는 다른 컨테이너의 `pg_dump`를 사용하면 클라이언트/서버 버전 차이로 restore 경고가 생길 수 있다.

```bash
ts=$(date +%Y%m%d_%H%M%S)

cd /home/dnhs02/iwantdataengineer/chartmaster
mkdir -p backups/postgres backups/manifests

docker exec chartmaster-postgres \
  pg_dump -U chartmaster chartmaster \
  | gzip > backups/postgres/chartmaster_metadata_${ts}_server2.sql.gz

sha256sum backups/postgres/chartmaster_metadata_${ts}_server2.sql.gz \
  > backups/manifests/chartmaster_metadata_${ts}_server2.sha256
```

검증:

```bash
gzip -t backups/postgres/chartmaster_metadata_${ts}_server2.sql.gz
sha256sum -c backups/manifests/chartmaster_metadata_${ts}_server2.sha256
```

## PostgreSQL 임시 복구 테스트

운영 DB를 덮어쓰지 않고 임시 DB를 만들어 복원한다.

```bash
ts=백업파일_타임스탬프
restore_db=chartmaster_restore_test_${ts}

cd /home/dnhs02/iwantdataengineer/chartmaster

docker exec chartmaster-postgres createdb -U chartmaster "$restore_db"

gunzip -c backups/postgres/chartmaster_metadata_${ts}_server2.sql.gz \
  | docker exec -i chartmaster-postgres \
      psql -v ON_ERROR_STOP=1 -U chartmaster -d "$restore_db"

docker exec chartmaster-postgres psql -U chartmaster -d "$restore_db" -Atc \
  "select count(*) from information_schema.tables where table_schema = 'public';"

docker exec chartmaster-postgres dropdb -U chartmaster "$restore_db"
```

정상 기준:

- `psql -v ON_ERROR_STOP=1` 복원 중 오류 없음
- public schema table count가 0보다 큼
- 임시 DB 삭제 완료

## 1차 백업 검증 기록

2026-08-23에 1차 백업과 복구 검증을 수행했다.

파일 저장소 백업:

```text
backups/files/chartmaster_files_20260823_005448.tar.gz
size: 30M
sha256: ecd48ed036e61638e1716fee04f083ede4fa08427ea58ab7352d60b7a193585d
검증: tar 목록 확인 완료
```

PostgreSQL metadata 백업:

```text
backups/postgres/chartmaster_metadata_20260823_005533_server2.sql.gz
size: 30K
sha256: 79e794598b079144105c550ee15721f5723c48469caeb0a9b4a7025f1d9f8c46
검증: gzip 무결성 확인, 임시 DB restore 성공, restored_tables=6, 임시 DB 삭제 완료
```

## 복구 절차 개요

파일 저장소 복구:

```bash
cd /home/dnhs02/iwantdataengineer/chartmaster
tar -xzf backups/files/chartmaster_files_YYYYMMDD_HHMMSS.tar.gz
```

PostgreSQL 복구:

```bash
target_db=chartmaster
backup=backups/postgres/chartmaster_metadata_YYYYMMDD_HHMMSS_server2.sql.gz

gunzip -c "$backup" \
  | docker exec -i chartmaster-postgres \
      psql -v ON_ERROR_STOP=1 -U chartmaster -d "$target_db"
```

운영 DB 복구는 기존 DB를 덮어쓸 수 있으므로 반드시 다음 순서로 진행한다.

1. 현재 운영 DB를 별도 이름으로 백업한다.
2. 복구 대상 DB 이름을 확인한다.
3. 임시 DB 복구 테스트를 먼저 수행한다.
4. 운영 DB 복구 여부를 명시적으로 결정한다.
5. 복구 후 FastAPI health, Airflow DAG, 품질 리포트를 확인한다.
