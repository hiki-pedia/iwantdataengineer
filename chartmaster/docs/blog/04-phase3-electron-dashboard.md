---
title: "Phase 3: Electron으로 시장 데이터 운영 화면 설계하기"
date: 2026-08-22 20:00:00 +0900
categories:
  - projects
tags:
  - electron
  - react
  - typescript
  - fastapi
  - data-quality
  - data-engineering
project_group: personal
project_order: 5
---

## Phase 3을 데이터 품질 작업 중간에 진행한 이유

ChartMaster의 Phase 1에서는 과거 OHLCV 백필과 Server 2 저장 구조를 만들었고, Phase 2에서는 Airflow로 한국장과 미국장 일봉 수집을 자동화했다. 이후 Phase 5 데이터 품질 작업으로 이동해 거래소 캘린더, 공급자 교차 검증, Curated 계층과 재처리를 구현하고 있었다.

데이터 품질과 모델링은 실제 데이터에서 새로운 문제가 발견될 때마다 계속 바뀔 수 있다. 반면 사용자가 어떤 정보를 어떤 화면에서 확인하고, API가 어떤 형태로 결과를 반환할지는 이후 구성 요소 전체에 영향을 준다. 모델을 먼저 만들고 화면을 나중에 붙이면 모델 출력과 UI 요구사항이 어긋나 다시 계약을 바꿀 가능성이 컸다.

따라서 Phase 5를 끝낸 뒤까지 기다리지 않고 Phase 3으로 잠시 분기했다. 목표는 완성된 투자 앱을 만드는 것이 아니라 다음 질문에 먼저 답하는 것이었다.

```text
수집한 데이터는 어디에서 확인할 것인가?
품질 경고는 어떤 단위로 보여줄 것인가?
아직 없는 예측과 리포트는 어떤 계약으로 연결할 것인가?
Electron이 Server 2 저장 구조를 몰라도 되게 만들 수 있는가?
```

## 구현 목표

Phase 3의 구현 범위는 다음과 같이 제한했다.

- Electron 기반 데스크톱 애플리케이션 구성
- React와 TypeScript를 이용한 화면 구현
- 검은 배경, 흰색 계열 텍스트, 네온 차트 색상 적용
- 29개 한국·미국 자산 탐색
- 전체 기간과 기간별 일봉 차트 제공
- 데이터 상태와 품질 이슈 확인
- 이벤트, 예측, 파이프라인, 리포트 화면의 정보 구조 정의
- Mock과 Live API가 같은 데이터 계약 사용
- 실제 모델이 없는 상태에서 가짜 예측값을 만들지 않기

## 기술 구성

| 영역 | 기술 | 역할 |
| --- | --- | --- |
| Desktop Runtime | Electron 43 | 로컬 데스크톱 실행 환경 |
| UI | React 18 | 화면과 상태 구성 |
| Language | TypeScript | API 응답과 화면 데이터 계약 정의 |
| Build | Vite 6 | 개발 서버와 프런트엔드 빌드 |
| Chart | Lightweight Charts 5 | 일봉, 거래량, 이동평균과 시계열 탐색 |
| API | FastAPI | Electron과 Server 2 사이의 읽기 전용 계층 |
| Runtime | Docker Compose | Server 1 API 컨테이너 실행과 자동 재시작 |

Electron 개발 환경은 Node.js 22를 기준으로 고정했다. 프로젝트 루트가 아닌 `chartmaster/desktop`에 `.nvmrc`, `package.json`, `package-lock.json`을 두어 로컬 PC에서도 같은 도구 버전을 재현하도록 했다.

## 화면 정보 구조

첫 화면부터 마케팅 페이지를 만들지 않고 실제 운영 화면으로 진입하도록 구성했다.

```text
시장
  Dashboard
  종목

데이터
  데이터 상태
  데이터 검증

분석
  이벤트
  예측
  파이프라인
  리포트
```

Dashboard는 전체 자산 수, 한국·미국 자산 수, 품질 경고 종목 수와 주요 변동 종목을 보여준다. 종목 상세 화면에서는 가격, 일간 수익률, 거래량, 데이터 기간, 품질 상태와 예측 준비 상태를 한 화면에서 비교한다.

![Dashboard 전체 화면](./images/phase3/01-dashboard-overview.png)

## Mock Provider로 화면 계약부터 고정하기

처음부터 Electron이 Server 2의 CSV나 PostgreSQL에 직접 접속하게 만들지 않았다. 화면은 `DashboardDataProvider` 인터페이스만 사용하고 데이터 공급자를 Mock과 API로 분리했다.

```text
DashboardDataProvider
  loadSnapshot()
  loadPrices(symbol, range)

MockDashboardDataProvider
ApiDashboardDataProvider
```

API 주소가 없으면 명시적인 Mock Snapshot을 사용한다. `VITE_CHARTMASTER_API_URL`이 설정되면 Live API를 사용한다. API 연결에 실패했을 때 자동으로 Mock으로 전환하지는 않는다. 운영 연결 실패를 가짜 데이터로 숨기면 화면만 보고 실제 시스템이 정상이라고 오해할 수 있기 때문이다.

이 구조를 통해 React 컴포넌트는 CSV 경로, SSH 사용자, PostgreSQL 비밀번호를 알 필요가 없다. 저장소가 Server 2 파일에서 S3로 바뀌어도 API 응답 계약이 유지되면 Electron 코드는 영향을 적게 받는다.

## 전체 이력을 유지하는 대화형 차트

종목 상세 차트는 다음 기능을 제공한다.

- `ALL / 5Y / 1Y / 6M / 1M / 5D` 구간 선택
- 날짜별 시가·고가·저가·종가·거래량 hover
- MA5와 MA20 이동평균
- 거래량 Histogram
- 마우스 drag를 이용한 과거 구간 이동
- 별도 확대 화면
- 향후 예측 가격 경로를 연결할 `forecastPoints` 계약

첫 구현에서는 기간 버튼을 누를 때 API에서 해당 기간의 데이터만 가져왔다. 최근 5년 데이터를 요청한 상태에서 차트를 왼쪽으로 이동하면 그보다 오래된 데이터가 클라이언트에 없으므로 빈 공간만 나타났다.

이를 다음 방식으로 변경했다.

```text
기존
  5Y 선택 -> 최근 5년 데이터만 API 요청 -> 이전 데이터 탐색 불가

변경
  종목 선택 -> ALL 데이터 한 번 요청
  5Y 선택 -> 전체 데이터는 유지하고 visible range만 최근 5년으로 설정
  왼쪽 drag -> 5년 이전 데이터 계속 탐색
```

차트 양끝을 넘어 빈 공간으로 이동하지 않도록 `fixLeftEdge`, `fixRightEdge`도 적용했다. 전체 이력은 최대 1만 6천 행 수준이므로 hover마다 배열 전체를 검색하지 않고 날짜를 키로 하는 Map을 만들어 조회 비용도 줄였다.

![종목 전체 기간 차트](./images/phase3/02-asset-chart-all.png)

![기간 선택 후 과거 탐색](./images/phase3/03-asset-chart-range.png)

## 예측 결과를 가짜로 채우지 않기

이 프로젝트의 최종 목표에는 가격 방향 예측과 예측선이 포함된다. 하지만 Phase 3 시점에는 학습과 시간순 검증을 통과한 모델이 없다.

화면을 채우기 위해 임의의 상승 확률이나 미래 가격을 생성하면 UI Mock과 실제 모델 결과를 구분하기 어려워진다. 따라서 현재 예측 계약은 다음 상태를 명시한다.

```json
{
  "status": "model_not_ready",
  "upProbability": null,
  "modelVersion": null,
  "trainedThrough": null,
  "forecastPoints": []
}
```

차트 예측 연장선은 `forecastPoints`가 존재할 때만 표시한다. 향후 모델은 예측 종가뿐 아니라 하한과 상한을 함께 제공할 수 있다.

## 품질 경고의 이유를 화면에서 확인하기

초기 Dashboard에는 `품질 관찰 11종목`, 종목 화면에는 `경고 2`처럼 개수만 표시했다. 이 표현만으로는 무엇을 확인해야 하는지 알 수 없었다.

이를 `품질 경고 종목`, `확인 필요`로 바꾸고 데이터 검증 화면에 다음 필드를 추가했다.

- 종목과 시장
- 오류 또는 경고
- 검사 코드
- 사람이 읽을 수 있는 설명
- 영향받은 행 수
- 검사 기준일
- 시장·심각도·검색 필터

현재 Server 2의 실제 최신 품질 리포트는 오류 0건, 경고 1건, 영향 종목 1개를 반환한다. 남은 경고는 SK하이닉스의 수정주가가 없거나 0 이하인 778행이다. `2007-03-02`는 임시공휴일로 확인되어 한국장 캘린더 예외에 반영했다. 미국장 17개 종목에는 현재 오류와 경고가 없다.

![데이터 검증 상세 화면](./images/phase3/04-data-quality-detail.png)

상세 이슈를 클릭하면 해당 종목 화면으로 이동한다. 품질 리포트에 해결 상태가 없는 항목은 UI에서 임의로 `해결` 또는 `미해결`로 판단하지 않는다.

## FastAPI로 서비스 경계 만들기

Phase 3의 Mock 계약을 실제 데이터와 연결하기 위해 Phase 4의 핵심 부분도 함께 구현했다.

```text
Local PC
Electron / React
      │ HTTP GET
      ▼
Server 1
FastAPI :8000
      │ SSH read
      ▼
Server 2
processed/features CSV
reports/data_quality JSON
```

FastAPI가 제공하는 엔드포인트는 다음과 같다.

```text
GET /health
GET /api/v1/dashboard
GET /api/v1/assets/{symbol}/prices?range=ALL|5Y|1Y|6M|1M|5D
GET /docs
```

Dashboard API는 29개 자산의 최신 가격과 데이터 기간, 품질 요약, 품질 이슈, 이벤트 후보, 예측 준비 상태, 파이프라인·리포트 표시 상태를 반환한다. 가격 API는 Server 2의 processed feature CSV에서 OHLCV와 이동평균을 읽는다.

![FastAPI Swagger 문서](./images/phase3/05-fastapi-docs.png)

## 구현 중 발생한 문제

### 1. 컨테이너 UID와 OpenSSH

API 컨테이너는 호스트 파일 권한과 맞추기 위해 UID 1000으로 실행했다. 하지만 Python Slim 이미지의 `/etc/passwd`에는 UID 1000 사용자가 없었다. OpenSSH는 키 파일 권한을 확인하기 전에 현재 UID의 사용자 정보를 찾으면서 다음 오류로 종료됐다.

```text
No user exists for uid 1000
```

API Dockerfile에 UID 1000 사용자를 명시적으로 생성해 해결했다. SSH 키는 컨테이너에 읽기 전용으로 마운트했다.

### 2. Airflow 상태를 데이터 최신일로 대체할 수 없는 문제

Airflow REST API 인증을 연결하지 않은 상태에서 데이터 최신일을 DAG의 최근 성공 시각처럼 표시하면 서로 다른 정보를 섞게 된다. 따라서 현재 파이프라인 실행 상태는 `unavailable`로 표시한다. 종목별 데이터 최신일은 별도 화면에서 실제 저장 결과로 보여준다.

### 3. API 장애를 Mock으로 숨기는 문제

Live API URL이 설정된 상태에서 요청이 실패하면 오류 화면을 표시한다. 자동 Mock 전환은 개발 중에는 편하지만 실제 API·SSH 장애를 발견하지 못하게 할 수 있어 사용하지 않았다.

## 검증 결과

구현 후 다음 항목을 확인했다.

| 검증 항목 | 결과 |
| --- | --- |
| Python 테스트 | 14개 통과 |
| Electron TypeScript 검사 | 통과 |
| Vite production build | 통과 |
| FastAPI 컨테이너 healthcheck | healthy |
| Server 2 자산 조회 | 29개 모두 조회 |
| 삼성전자 ALL 가격 조회 | 6,663행 |
| 삼성전자 데이터 기간 | 2000-01-04~2026-08-21 |
| 품질 이슈 API | 오류 0, 경고 1, 영향 종목 1 |

## Phase 3에서 학습한 내용

### 화면이 API 계약을 구체화한다

`예측 결과를 보여준다`는 요구만으로는 API를 정의할 수 없다. 기준일, 목표일, 예측 기간, 모델 버전, 학습 데이터 기준일, 평가 지표, 불확실성 범위가 화면에 필요하다는 사실을 UI를 만들면서 구체화했다.

### 데이터 상태와 실행 상태는 다르다

최신 CSV가 존재한다는 사실과 Airflow DAG가 성공했다는 사실은 같은 정보가 아니다. 사용자가 보는 화면에서도 최종 데이터 상태와 오케스트레이터 실행 상태를 분리해야 한다.

### Mock은 가짜 성공 상태가 아니다

Mock Provider는 화면 계약을 개발하기 위한 명시적인 공급자다. Live API 장애 시 자동으로 나타나는 대체 화면으로 사용하면 안 된다.

### Electron은 저장소 클라이언트가 아니다

Electron이 SSH와 DB 접속 정보를 가지면 배포, 보안, 저장소 이전이 어려워진다. FastAPI를 경계로 두면서 클라이언트는 HTTP 계약만 알고 데이터 위치는 서버가 책임지게 했다.

## 남은 범위

Phase 3 화면 구조는 완료했지만 다음 기능은 후속 Phase에서 실제 결과와 연결한다.

- Airflow REST API 인증과 실제 DAG Run·Task 상태
- 모델 학습 후 상승 확률과 가격 경로
- RAG 기반 급등·급락 외부 요인
- 종목별 AI 리포트
- 설정과 사용자 관심 종목
- API 인증, 접근 제어와 운영 배포

이후 Phase 5로 돌아가 데이터 품질 검사, curated 계층, 재처리, Airflow 품질 Gate를 마무리했다. KRX 인증 원천 검증과 장애 주입 테스트는 Phase 6 이후 운영 안정성 보강 항목으로 분리했다.

## 포트폴리오 문장

```text
데이터 품질과 모델 출력이 계속 바뀌는 상황에서 Electron 기반 운영 대시보드의 정보 구조를 먼저 설계하고, Mock/Live Provider가 동일한 TypeScript 계약을 사용하도록 구성했습니다. Server 1의 FastAPI가 Server 2 저장소를 읽는 서비스 경계를 구현해 클라이언트의 SSH·DB 직접 접근을 제거했으며, 전체 기간 시계열 탐색과 종목별 품질 이슈 조회를 실제 29개 자산 데이터에 연결했습니다.
```

---

마지막 확인일: 2026-08-22
