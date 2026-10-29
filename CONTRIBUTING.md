# 작업 안내

기준 브랜치는 `main`입니다. 작업을 시작할 때 원격 변경을 받고 목적별로 브랜치를 만듭니다.

```bash
git switch main
git pull --ff-only
git switch -c fix/market-data-gap
```

기능은 `feat/`, 버그 수정은 `fix/`, 문서는 `docs/`, 자동화 설정은 `ci/`를 사용합니다.
기존 `server`, `local` 브랜치에서 진행 중인 작업은 유지합니다.

## 커밋과 PR

파일 수보다 변경 목적을 기준으로 커밋을 나눕니다. 데이터 처리 방식 변경과 문서 오탈자 수정은 따로 남깁니다.
제목에는 바뀐 동작을 적습니다.

```text
수집: 누락 구간을 찾을 때 거래일 기준 적용
API: 오래된 예측 결과에 기준일 표시
자동화: PR에서 테스트와 데스크톱 빌드 실행
```

이유가 제목만으로 드러나지 않으면 본문에 원인과 선택한 방법을 적습니다.
PR에는 변경 이유, 실행한 검사, 남은 확인 사항을 적습니다. 검사하지 않은 항목은 그대로 남겨둡니다.

## 확인할 범위

- Python 변경: 루트에서 `PYTHONPATH=chartmaster/src python -m pytest chartmaster/tests -q`
- 화면·타입 변경: `chartmaster/desktop`에서 `npm ci && npm run build`
- 데이터 처리 변경: 기존 데이터 병합, 중복 처리, 날짜 경계에 대한 테스트
- API 응답 변경: Python 스키마와 `chartmaster/desktop/src/data/contracts.ts` 양쪽 확인
- 서버·Airflow 변경: 영향받는 DAG와 재실행 방법을 기록하고 실제 서버 확인 결과를 별도로 작성

CI 통과만으로 운영 서버에서 확인했다고 기록하지 않습니다.

## 데이터와 이력

`.env`, 수집 원본, 모델 가중치는 커밋하지 않습니다. 공유할 설정은 `.env.example`에 값 없는 예시로 남깁니다.
지표나 예측 결과를 갱신할 때는 데이터 기준일, 모델 버전, 비교 대상을 함께 기록합니다.

병합된 변경을 되돌릴 때는 `git revert <커밋>`으로 되돌린 이유를 남깁니다.
DB나 저장 데이터가 바뀌었다면 코드만 되돌려서는 복구되지 않으므로
[재처리 절차](chartmaster/docs/backfill-reprocessing-runbook.md)와
[복원 절차](chartmaster/docs/backup-restore-runbook.md)를 함께 확인합니다.
