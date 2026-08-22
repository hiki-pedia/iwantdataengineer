# FastAPI 데이터 제공 계층

## 목적

Electron이 서버2의 파일이나 PostgreSQL에 직접 접근하지 않도록 서버1에 읽기 전용 API 계층을 둔다. 클라이언트는 저장 위치, SSH 인증 정보, 파일 구조를 알 필요 없이 HTTP 응답 계약만 사용한다.

```text
로컬 PC Electron
  -> HTTP GET
서버1 FastAPI (:8000)
  -> SSH 읽기
서버2 raw / processed / curated / reports
```

FastAPI와 Airflow는 같은 서버1에서 실행되지만 역할은 분리한다. Airflow는 데이터를 수집하고 가공하며, FastAPI는 이미 저장된 데이터를 조회해 클라이언트에 제공한다.

## 엔드포인트

```text
GET /health
GET /api/v1/dashboard
GET /api/v1/assets/{symbol}/prices?range=5Y|1Y|6M|1M|5D
GET /docs
```

대시보드 응답은 자산 최신값, 데이터 품질, 파이프라인 표시 상태, 급등락 후보, 예측 상태와 리포트 상태를 포함한다. 가격 API는 서버2의 `processed/features` CSV에서 OHLCV와 이동평균을 반환한다.

현재 예측 모델은 아직 학습하지 않았으므로 예측값과 예측선을 만들지 않는다. Airflow API 인증도 연결하지 않았으므로 파이프라인 상태는 `unavailable`로 명시한다. 실제 데이터와 구현되지 않은 결과를 구분하기 위한 설계다.

## 실행

```bash
cd /home/dnhs01/iwantdataengineer/chartmaster
docker compose --env-file ../.env up -d --build chartmaster-api
docker compose --env-file ../.env ps chartmaster-api
curl http://127.0.0.1:8000/health
```

Compose의 `restart: unless-stopped` 때문에 Docker 서비스가 부팅할 때 시작되면 API 컨테이너도 다시 시작된다. 사용자가 명시적으로 컨테이너를 중지한 경우에는 자동 시작하지 않는다.

## 로컬 Electron 연결

로컬 PC에서 `chartmaster/desktop/.env.local`을 만든다.

```dotenv
VITE_CHARTMASTER_API_URL=http://192.168.0.5:8000
```

Vite 개발 서버의 출처는 기본 CORS 허용 목록에 포함되어 있다. API는 아직 인증이 없으므로 인터넷에 직접 공개하지 않고 LAN 또는 WireGuard 내부에서만 사용한다.
