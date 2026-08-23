# ChartMaster 차트 기반 알고리즘 계획

## 목적

ChartMaster의 Phase 7은 단순히 "주가를 맞히는 AI"를 만드는 단계가 아니다. 프로젝트의 관점은 기업 가치 분석보다 차트 분석에 가깝다.

따라서 Phase 7의 목표는 다음과 같이 정의한다.

```text
OHLCV와 기술적 지표를 이용해 차트 기반 예측 알고리즘을 단계적으로 비교하고,
예측 성능과 실제 투자 성능을 함께 평가한다.
```

## 핵심 관점

주식 가격에는 기업 실적, 금리, 환율, 정책, 심리 같은 외부 요인이 모두 영향을 준다. Phase 7에서는 이 전체를 한 번에 설명하려 하지 않는다.

먼저 차트 분석가들이 실제로 보는 가격·거래량 패턴을 수치화하고, 그 신호가 다음 기간의 방향성 또는 수익률과 얼마나 연결되는지 검증한다.

즉 Phase 7의 첫 질문은 다음이다.

```text
기술적 지표와 차트 패턴만으로 5거래일 뒤 방향성을 baseline보다 잘 예측할 수 있는가?
```

## 국내장 장기 횡보 구간 문제

국내장 데이터는 2000년 이후부터 확보되어 있지만, 2020년 이전 구간에는 장기 횡보가 많다. 이 구간을 무조건 전체 학습에 넣으면 모델이 횡보장 특성을 과하게 학습할 수 있다.

따라서 Phase 7에서는 학습 데이터 구간을 분리해 비교한다.

```text
Dataset A: 전체 기간
Dataset B: 2020년 이후
Dataset C: 최근 5년
```

비교 목적:

- 장기 횡보 구간이 모델 성능에 미치는 영향 확인
- 최근 시장 구조에서 더 잘 작동하는 지표 확인
- 국내장과 미국장 차이 확인
- core 종목과 experimental 종목 차이 확인

포트폴리오 설명:

```text
국내장 장기 횡보 구간이 모델 학습에 미치는 영향을 확인하기 위해 전체 기간 데이터와 2020년 이후 데이터를 분리해 학습하고, 예측 성능과 백테스트 성과를 비교했다.
```

## 입력 데이터

기본 입력:

- Open
- High
- Low
- Close
- Adjusted Close
- Volume
- Turnover Value

기술적 지표:

- MA5, MA20, MA60, MA120
- EMA
- RSI
- MACD, MACD signal, MACD histogram
- Bollinger Band upper/lower
- Bollinger percent b
- Bollinger bandwidth
- ATR
- Momentum
- 과거 수익률
- 변동성
- 거래량 변화율
- 20일/60일 고점 돌파 여부
- 20일/60일 저점 이탈 여부

## 문제 정의 후보

Phase 7의 첫 문제는 분류 문제로 시작한다.

```text
5거래일 뒤 종가가 현재 종가보다 상승할 것인가?
```

Target:

```text
positive_return_5d
```

후속 확장 후보:

- 1거래일 뒤 수익률 회귀
- 5거래일 뒤 수익률 회귀
- 20거래일 뒤 상승 여부
- 급등/급락 이벤트 예측
- BUY / HOLD / SELL 분류
- 변동성 확대 여부 예측

## 알고리즘 단계

### 1. Naive Baseline

목적:

- ML 모델이 실제로 의미 있는지 비교할 기준을 만든다.

후보:

- 항상 상승 예측
- 직전 5일 수익률 방향을 그대로 따른다.
- 20일 이동평균 위면 상승, 아래면 하락으로 본다.
- Buy & Hold와 비교한다.

### 2. ARIMA

역할:

- 전통적인 시계열 baseline
- 가격 또는 수익률의 자기상관 기반 예측
- 복잡한 AI 모델과 비교하기 위한 기준선

주의:

- 개별 종목별 학습 비용이 커질 수 있다.
- 차트 지표 기반 분류와 직접 비교하기보다 회귀 baseline으로 분리한다.
- Phase 7 1차 구현에서는 보류하고, ML baseline 이후 추가한다.

### 3. Logistic Regression

역할:

- 가장 단순한 분류 모델
- feature scaling, class imbalance, threshold 조정을 학습하기 좋다.
- 해석 가능한 baseline으로 사용한다.

### 4. Random Forest

역할:

- RSI, MACD, MA, 거래량 변화율 같은 비선형 관계를 학습한다.
- feature importance로 어떤 지표가 중요했는지 확인할 수 있다.
- 초기 ML baseline으로 적합하다.

### 5. XGBoost

역할:

- 주식 예측 프로젝트에서 자주 쓰이는 gradient boosting 계열 모델
- 기술적 지표 기반 tabular feature와 잘 맞는다.
- feature importance와 성능 비교가 쉽다.

주의:

- 의존성을 추가해야 하므로 Phase 7 1차에서는 scikit-learn 모델을 먼저 완성하고, 이후 추가한다.

### 6. LSTM / GRU

역할:

- 최근 30일, 60일 같은 연속 시계열을 입력으로 사용한다.
- 가격 흐름의 시간적 패턴을 학습한다.

주의:

- tabular ML보다 데이터 준비가 복잡하다.
- baseline보다 나은지 반드시 검증해야 한다.
- Phase 7 후반 또는 Phase 8 이후 실험으로 미룬다.

### 7. CNN / CNN-LSTM

역할:

- 일정 구간 안의 국소 패턴을 찾는다.
- 캔들 흐름이나 차트 이미지를 패턴으로 볼 때 사용할 수 있다.

주의:

- 이미지 기반 차트 인식으로 가면 데이터 생성 방식이 크게 달라진다.
- 먼저 시계열 feature 기반 CNN을 검토한다.

### 8. Transformer

역할:

- attention으로 긴 기간의 관계를 학습한다.
- 금융 시계열 연구에서 자주 등장한다.

주의:

- 데이터 수와 실험 비용이 크다.
- baseline, XGBoost, LSTM 결과가 나온 뒤 비교 대상으로 추가한다.

### 9. Reinforcement Learning

역할:

- 가격 자체 예측보다 BUY / HOLD / SELL 행동을 학습한다.
- Reward를 투자 수익률 또는 risk-adjusted return으로 둔다.

주의:

- 환경 설계, 수수료, 슬리피지, 보상 함수에 따라 결과가 크게 달라진다.
- Phase 7의 핵심 범위가 아니라 후속 고급 실험으로 둔다.

### 10. Ensemble

역할:

- XGBoost, LSTM, Transformer 등의 예측을 결합한다.
- 단순 평균, weighted average, voting부터 시작한다.

주의:

- 개별 모델의 검증이 끝난 뒤 진행한다.

## Phase 7 구현 순서

Phase 7은 너무 커질 수 있으므로 1차 목표를 좁힌다.

```text
Phase 7-1: 기술적 지표 feature 생성
Phase 7-2: 5거래일 뒤 상승 여부 target 생성
Phase 7-3: 전체 기간 / 2020년 이후 / 최근 5년 dataset 분리
Phase 7-4: Naive baseline
Phase 7-5: Logistic Regression
Phase 7-6: Random Forest
Phase 7-7: metric 저장
Phase 7-8: 간단한 backtest
```

후속 확장:

```text
ARIMA
XGBoost
LSTM / GRU
CNN / CNN-LSTM
Transformer
Ensemble
Reinforcement Learning
```

## 평가 지표

예측 성능:

- Accuracy
- Precision
- Recall
- F1-score
- ROC-AUC
- MAE
- RMSE

투자 성능:

- 누적 수익률
- 연환산 수익률
- Sharpe Ratio
- MDD
- 승률
- 거래 횟수
- 수수료
- 슬리피지
- Buy & Hold 대비 성과

## 검증 원칙

랜덤 split은 사용하지 않는다.

주식 데이터는 시간 순서가 있으므로 과거로 학습하고 미래로 검증한다.

예시:

```text
train: 과거 구간
validation: 중간 구간
test: 가장 최근 구간
```

비교할 dataset:

```text
전체 기간 모델
2020년 이후 모델
최근 5년 모델
```

비교할 시장:

```text
한국장
미국장
전체
```

비교할 자산 tier:

```text
core
experimental
all
```

## Phase 7 완료 기준

- 차트 분석용 기술적 지표 feature를 생성했다.
- `positive_return_5d` target을 생성했다.
- 전체 기간, 2020년 이후, 최근 5년 dataset을 비교했다.
- naive baseline을 평가했다.
- Logistic Regression을 학습했다.
- Random Forest를 학습했다.
- 예측 metric을 저장했다.
- 간단한 backtest metric을 계산했다.
- 모델 artifact와 metric을 Server 2에 저장했다.
- PostgreSQL metadata에 모델 버전과 metric을 기록했다.
- Phase 7 블로그에 결과와 한계를 정리했다.

## 포트폴리오 설명 문장

OHLCV와 RSI, MACD, 이동평균선, Bollinger Band, ATR 등 기술적 지표를 기반으로 차트 예측 알고리즘을 단계적으로 비교했습니다. 국내장 장기 횡보 구간의 영향을 확인하기 위해 전체 기간, 2020년 이후, 최근 5년 데이터셋을 분리해 학습했고, naive baseline, Logistic Regression, Random Forest를 예측 성능과 백테스트 성능으로 함께 평가했습니다. 이후 XGBoost, LSTM, Transformer, Ensemble로 확장할 수 있도록 모델 artifact와 metric 저장 구조를 설계했습니다.
