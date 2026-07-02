Caregent 기술 명세서 (Technical Specification)

0. v1 학습 범위

Caregent v1은 전체 서비스 완성이 아니라 데이터 엔지니어링 학습을 목표로 한다.

v1 포함 범위

* Local Airflow
* PostgreSQL
* 샘플 채용공고 데이터 수집
* 중복 제거
* 기술스택 추출
* 직무/산업군 분류
* PostgreSQL 적재
* 기술스택 빈도 분석
* Airflow 실행 로그와 retry 확인

v1 제외 범위

* Electron Desktop Application
* 실서비스용 AI Agent
* Vector Database
* RAG 시스템
* AWS 배포

AWS는 v1 이후 S3, EC2, CloudWatch 순서로 확장한다.

⸻

1. 시스템 개요

Caregent는 채용시장 데이터를 자동 수집하고 분석하여 사용자 맞춤형 취업 전략을 제공하는 AI Career Agent 플랫폼이다.

시스템은 데이터 수집 계층, 데이터 저장 계층, AI 분석 계층, 사용자 인터페이스 계층으로 구성된다.

⸻

2. 전체 시스템 아키텍처

Electron Desktop Application

↓

FastAPI Backend

↓

AI Career Agent

↓

Database

↑

Airflow ETL Pipeline

↓

Crawler

↓

채용 데이터 소스

⸻

3. 물리적 서버 구성

Server 1 (Application Server)

운영체제

* Ubuntu 22.04 LTS

주요 역할

* Apache Airflow
* ETL Pipeline
* Data Crawler
* FastAPI Backend
* Docker

기능

* 채용공고 수집
* 데이터 전처리
* AI Agent 요청 처리
* API 서비스 제공

⸻

Server 2 (Database Server)

운영체제

* Ubuntu 22.04 LTS

주요 역할

* Database Server
* Data Storage
* Backup Storage

저장공간

* SSD : 운영체제
* HDD : 데이터 저장

기능

* 채용공고 데이터 저장
* 사용자 프로필 저장
* 분석 결과 저장
* 백업 데이터 저장

⸻

Network

구성

* WireGuard VPN

기능

* 서버 간 통신
* 내부망 구성
* 데이터 전송 보안

⸻

4. 기술 스택

Desktop Application

Electron

기능

* 채용공고 조회
* AI Agent 채팅
* 역량 분석 결과 시각화
* 기술 트렌드 조회

⸻

Backend

FastAPI

기능

* REST API 제공
* 사용자 요청 처리
* Agent 호출
* 데이터 조회

⸻

Data Pipeline

Apache Airflow

기능

* 스케줄링
* ETL 관리
* 작업 모니터링
* 실패 작업 재시도

실행 주기

* 매일 오후 3시

⸻

Database

v1 선정

* PostgreSQL

후속 검토

* MongoDB

선정 기준

* 데이터 구조
* 검색 성능
* 확장성

⸻

AI Layer

LLM API

후보

* OpenAI
* Claude
* GLM

기능

* 자연어 이해
* 채용시장 분석
* Skill Gap Analysis
* 커리어 전략 생성

⸻

5. 데이터 수집 파이프라인

Step 1

채용 데이터 수집

Airflow Scheduler

↓

Crawler

↓

기업 채용 사이트

↓

채용 플랫폼

↓

기술 채용 게시판

⸻

Step 2

데이터 정제

수집 데이터

↓

중복 제거

↓

기술스택 추출

↓

직무 분류

↓

산업군 분류

↓

정규화

⸻

Step 3

데이터 저장

정제 데이터

↓

Database 저장

⸻

Step 4

시장 분석 데이터 생성

채용공고

↓

기술스택 빈도 분석

↓

트렌드 분석

↓

통계 생성

↓

AI Agent 활용

⸻

6. AI Agent 구조

사용자 질문

↓

Intent Analysis

↓

Tool Selection

↓

Data Retrieval

↓

Reasoning

↓

Response Generation

⸻

지원 기능

Career Analysis

Skill Gap Analysis

Job Recommendation

Learning Recommendation

Market Trend Analysis

⸻

7. Skill Gap Analysis 알고리즘

입력

사용자 기술스택

↓

채용시장 기술스택

↓

비교

↓

부족 기술 도출

↓

중요도 계산

↓

학습 우선순위 생성

⸻

예시

사용자

Python

FastAPI

PostgreSQL

↓

시장 요구

Python

PostgreSQL

AWS

Docker

Airflow

↓

결과

1. AWS
2. Docker
3. Airflow

⸻

8. 데이터 모델

Users

* user_id
* name
* email

⸻

UserSkills

* user_id
* skill_name
* level

⸻

Jobs

* company_name
* position
* category
* location
* deadline
* url

⸻

JobSkills

* job_id
* skill_name

⸻

TrendData

* skill_name
* frequency
* trend_score

⸻

9. 향후 확장 계획

Phase 2

* Vector Database
* RAG 시스템
* 문서 검색

Phase 3

* GitHub 분석
* 이력서 분석
* 포트폴리오 분석

Phase 4

* 음성 인터페이스
* AI 면접관
* AI 커리어 코치

Phase 5

* AWS 클라우드 마이그레이션
* GPU 기반 모델 활용
* 대규모 데이터 분석
