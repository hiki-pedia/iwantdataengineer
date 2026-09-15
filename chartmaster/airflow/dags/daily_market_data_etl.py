"""Scheduled ChartMaster market data ETL DAGs."""

from __future__ import annotations

from datetime import timedelta

import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator


PROJECT_DIR = "/opt/airflow/chartmaster"
LOOKBACK_DAYS = 5
MISSING_BLOCK_SIZE = 5
MAX_MISSING_BLOCKS = 52
PREDICTION_SEQUENCE_LENGTH = 60
PREDICTION_EPOCHS = 3
PREDICTION_BATCH_SIZE = 512

DEFAULT_ARGS = {
    "owner": "chartmaster",
    "depends_on_past": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=20),
}


def market_etl_command(market: str, market_timezone: str) -> str:
    return f"""
    set -euo pipefail
    cd {PROJECT_DIR}
    START_DATE="$(python - <<'PY'
import pendulum
print(pendulum.now("{market_timezone}").subtract(days={LOOKBACK_DAYS}).to_date_string())
PY
)"
    END_DATE="$(python - <<'PY'
import pendulum
print(pendulum.now("{market_timezone}").add(days=1).to_date_string())
PY
)"
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH={PROJECT_DIR}/src \
      python -m chartmaster.pipelines.local_market_data_etl \
        --market {market} \
        --tier all \
        --start "$START_DATE" \
        --end "$END_DATE" \
        --missing-block-size {MISSING_BLOCK_SIZE} \
        --max-missing-blocks {MAX_MISSING_BLOCKS}
    """


def market_quality_command(market: str, market_timezone: str) -> str:
    return f"""
    set -euo pipefail
    cd {PROJECT_DIR}
    AS_OF="$(python - <<'PY'
import pendulum
print(pendulum.now("{market_timezone}").to_date_string())
PY
)"
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH={PROJECT_DIR}/src \
      python -m chartmaster.pipelines.local_market_data_quality \
        --market {market} \
        --tier all \
        --as-of "$AS_OF"
    """


def kr_market_curate_command() -> str:
    return f"""
    set -euo pipefail
    cd {PROJECT_DIR}
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH={PROJECT_DIR}/src \
      python -m chartmaster.pipelines.local_kr_market_data_curate \
        --tier all
    """


def market_prediction_command(market: str, market_timezone: str) -> str:
    return f"""
    set -euo pipefail
    cd {PROJECT_DIR}
    AS_OF="$(python - <<'PY'
import pendulum
print(pendulum.now("{market_timezone}").to_date_string())
PY
)"
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH={PROJECT_DIR}/src \
      python -m chartmaster.pipelines.local_transformer_direction_prediction \
        --market {market} \
        --tier all \
        --window all_history \
        --as-of "$AS_OF" \
        --sequence-length {PREDICTION_SEQUENCE_LENGTH} \
        --epochs {PREDICTION_EPOCHS} \
        --batch-size {PREDICTION_BATCH_SIZE}
    """


with DAG(
    dag_id="daily_kr_market_data_etl",
    description="Collect Korean market daily OHLCV after KRX close.",
    default_args=DEFAULT_ARGS,
    schedule="10 16 * * 1-5",
    start_date=pendulum.datetime(2026, 7, 27, tz="Asia/Seoul"),
    catchup=True,
    max_active_runs=1,
    tags=["chartmaster", "market-data", "kr"],
) as kr_market_dag:
    collect_kr = BashOperator(
        task_id="collect_kr_daily_ohlcv",
        bash_command=market_etl_command("KR", "Asia/Seoul"),
    )
    validate_kr = BashOperator(
        task_id="validate_kr_market_data",
        bash_command=market_quality_command("KR", "Asia/Seoul"),
    )
    predict_kr = BashOperator(
        task_id="predict_kr_direction_5d",
        bash_command=market_prediction_command("KR", "Asia/Seoul"),
        execution_timeout=timedelta(hours=2),
    )
    curate_kr = BashOperator(
        task_id="curate_kr_market_data",
        bash_command=kr_market_curate_command(),
    )
    collect_kr >> curate_kr >> validate_kr >> predict_kr


with DAG(
    dag_id="daily_us_market_data_etl",
    description="Collect US market daily OHLCV after US regular close.",
    default_args=DEFAULT_ARGS,
    schedule="30 17 * * 1-5",
    start_date=pendulum.datetime(2026, 7, 27, tz="America/New_York"),
    catchup=True,
    max_active_runs=1,
    tags=["chartmaster", "market-data", "us"],
) as us_market_dag:
    collect_us = BashOperator(
        task_id="collect_us_daily_ohlcv",
        bash_command=market_etl_command("US", "America/New_York"),
    )
    validate_us = BashOperator(
        task_id="validate_us_market_data",
        bash_command=market_quality_command("US", "America/New_York"),
    )
    predict_us = BashOperator(
        task_id="predict_us_direction_5d",
        bash_command=market_prediction_command("US", "America/New_York"),
        execution_timeout=timedelta(hours=2),
    )
    collect_us >> validate_us >> predict_us
