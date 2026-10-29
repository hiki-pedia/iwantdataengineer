# iwantdataengineer

시장 데이터를 수집하고, 다시 처리하고, 모델 결과를 조회하는 과정을 만드는 개인 프로젝트입니다.
현재는 ChartMaster를 개발하고 있습니다.

## ChartMaster

한국·미국 주식과 ETF 데이터를 Airflow로 수집합니다. 원본과 가공 데이터를 분리해 저장하고,
PostgreSQL에 실행 이력을 남깁니다. FastAPI가 저장된 결과를 읽고, Electron 화면에서 차트와 데이터 품질을 확인합니다.

- 수집: 누락 구간을 보충하고 중복 날짜를 병합하는 일별 ETL
- 검증: 거래일 기준 누락 검사, 한국 시장 OHLC 보정, 가공 데이터 재생성
- 모델: Random Forest, XGBoost, LSTM, Transformer 방향성 분류 실험
- 조회: FastAPI와 Electron 사이의 데이터 계약, 저장된 예측 결과의 최신 여부 확인
- 운영 기록: 백업·복원 절차와 장애 실험 결과

현재 코드는 로컬 서버 환경을 기준으로 합니다. AWS S3/RDS 이전과 SageMaker 연동은 이후 단계로 남겨두었습니다.

| 확인할 내용 | 문서 |
| --- | --- |
| 실행 방법과 개발 단계 | [ChartMaster](chartmaster/README.md) |
| 서버·저장소·API 구조 | [구조 설명](chartmaster/docs/architecture.md) |
| 데이터 품질 기준 | [검증 기준](chartmaster/docs/data-quality-strategy.md) |
| 누락 데이터 재처리 | [재처리 절차](chartmaster/docs/backfill-reprocessing-runbook.md) |
| 백업과 복원 | [복원 절차](chartmaster/docs/backup-restore-runbook.md) |
| 장애를 넣고 확인한 결과 | [장애 실험](chartmaster/docs/failure-drill-report.md) |

## 변경 후 확인

Python 3.11과 Node.js 22를 사용합니다. 아래 명령은 저장소 루트에서 실행합니다.
Python 의존성의 `torch==2.5.1+cpu`는 Linux CPU 환경용입니다.
macOS에서는 같은 버전의 macOS용 PyTorch가 필요합니다.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r chartmaster/requirements.txt
PYTHONPATH=chartmaster/src python -m pytest chartmaster/tests -q
```

테스트는 임시 파일과 테스트 데이터를 사용합니다. 서버 SSH, 운영 DB, OpenAI 키를 설정할 필요는 없습니다.

```bash
cd chartmaster/desktop
npm ci
npm run build
```

PR에서는 Python 테스트와 데스크톱 빌드를 각각 실행합니다.
서버 연결, Airflow 실제 실행, 모델 학습 성능은 이 검사에 포함되지 않습니다.
서버 설정을 바꿀 때는 해당 환경에서 확인한 내용도 PR에 남깁니다.

브랜치와 커밋 작성 방법은 [작업 안내](CONTRIBUTING.md)에 정리했습니다.
