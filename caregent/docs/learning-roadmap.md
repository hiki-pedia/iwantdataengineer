# Caregent Learning Roadmap

Caregent는 완성형 서비스보다 데이터 엔지니어링 학습과 포트폴리오 증명을 우선하는 프로젝트다. 각 단계는 결과물보다 "무엇을 배웠고 어떻게 검증했는가"를 남기는 데 집중한다.

## Phase 1: Local Airflow + PostgreSQL

목표:

- Airflow DAG 구조, 스케줄, task, retry, log를 이해한다.
- 원천 데이터 수집, 정제, 적재, 집계로 이어지는 ETL 흐름을 만든다.
- PostgreSQL 테이블과 idempotent load 개념을 익힌다.

실습 결과:

- `daily_job_etl` DAG
- 샘플 채용공고 JSON
- `jobs`, `job_skills`, `trend_data` PostgreSQL 테이블
- 기술스택 빈도 집계

포트폴리오 설명 문장:

> Airflow로 매일 실행되는 채용공고 ETL DAG를 구성하고, 중복 제거와 기술스택 추출 후 PostgreSQL에 idempotent하게 적재했습니다.

## Phase 2: AWS S3

목표:

- S3를 raw/staging 저장소로 사용하는 패턴을 익힌다.
- 로컬 파일 기반 extract를 S3 object 기반 extract로 확장한다.
- IAM user/role, access key, bucket policy의 차이를 학습한다.

예정 결과:

- Raw job JSON을 S3에 저장
- Airflow task에서 S3 object 읽기
- 로컬 PostgreSQL 적재 유지

## Phase 3: EC2 or Docker Deployment

목표:

- Docker Compose 서비스를 EC2에 올려 운영 환경의 기본을 경험한다.
- 보안 그룹, 포트, 환경변수, 볼륨, 재시작 정책을 학습한다.

예정 결과:

- EC2 기반 Airflow + PostgreSQL 실습 환경
- 운영 체크리스트

## Phase 4: Monitoring and Backup

목표:

- Airflow 로그와 실패 retry를 관찰한다.
- PostgreSQL 백업과 복구 흐름을 실습한다.
- CloudWatch 같은 운영 모니터링 개념으로 확장한다.

예정 결과:

- 실패 케이스 재현 기록
- 백업/복구 명령 기록
- 운영 회고 문서

## Study Log Template

매 실습 후 아래 내용을 남긴다.

- Date:
- Goal:
- Concepts:
- Commands:
- Result:
- Failure:
- Fix:
- Portfolio note:

