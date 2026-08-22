"""Scheduled ChartMaster market data ETL DAGs."""

from __future__ import annotations

from datetime import timedelta

import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator


PROJECT_DIR = "/opt/airflow/chartmaster"
LOOKBACK_DAYS = 10

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
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH={PROJECT_DIR}/src \
      python -m chartmaster.pipelines.local_market_data_etl \
        --market {market} \
        --tier all \
        --start "{{{{ macros.ds_add(data_interval_end.in_timezone('{market_timezone}').to_date_string(), -{LOOKBACK_DAYS}) }}}}" \
        --end "{{{{ macros.ds_add(data_interval_end.in_timezone('{market_timezone}').to_date_string(), 1) }}}}"
    """


def market_quality_command(market: str, market_timezone: str) -> str:
    return f"""
    set -euo pipefail
    cd {PROJECT_DIR}
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH={PROJECT_DIR}/src \
      python -m chartmaster.pipelines.local_market_data_quality \
        --market {market} \
        --tier all \
        --as-of "{{{{ data_interval_end.in_timezone('{market_timezone}').to_date_string() }}}}"
    """


def kr_market_curate_command() -> str:
    return f"""
    set -euo pipefail
    cd {PROJECT_DIR}
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH={PROJECT_DIR}/src \
      python -m chartmaster.pipelines.local_kr_market_data_curate \
        --tier all
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
    curate_kr = BashOperator(
        task_id="curate_kr_market_data",
        bash_command=kr_market_curate_command(),
    )
    collect_kr >> curate_kr >> validate_kr


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
    collect_us >> validate_us
