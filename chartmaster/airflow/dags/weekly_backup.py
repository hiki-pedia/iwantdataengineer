"""Weekly verified backup for ChartMaster server2 data and metadata."""

from __future__ import annotations

from datetime import timedelta

import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator


PROJECT_DIR = "/opt/airflow/chartmaster"


with DAG(
    dag_id="weekly_chartmaster_backup",
    description="Back up and verify server2 files and ChartMaster PostgreSQL metadata.",
    default_args={
        "owner": "chartmaster",
        "depends_on_past": False,
        "retries": 2,
        "retry_delay": timedelta(minutes=30),
    },
    schedule="0 3 * * 0",
    start_date=pendulum.datetime(2026, 10, 25, tz="Asia/Seoul"),
    catchup=False,
    max_active_runs=1,
    tags=["chartmaster", "backup", "operations"],
) as backup_dag:
    BashOperator(
        task_id="backup_and_verify_server2",
        bash_command=f"""
        set -euo pipefail
        cd {PROJECT_DIR}
        PYTHONDONTWRITEBYTECODE=1 PYTHONPATH={PROJECT_DIR}/src \
          python -m chartmaster.pipelines.local_server2_backup
        """,
        execution_timeout=timedelta(hours=4),
    )
