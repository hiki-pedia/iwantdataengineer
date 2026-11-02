from pathlib import Path


def test_daily_market_dag_runs_prediction_after_quality() -> None:
    dag_source = Path("chartmaster/airflow/dags/daily_market_data_etl.py").read_text(encoding="utf-8")

    assert "predict_kr_direction_5d" in dag_source
    assert "predict_us_direction_5d" in dag_source
    assert "chartmaster.pipelines.local_transformer_direction_prediction" in dag_source
    assert "collect_kr >> curate_kr >> validate_kr >> predict_kr" in dag_source
    assert "collect_us >> validate_us >> predict_us" in dag_source


def test_daily_market_dag_uses_one_latest_run_and_recursive_missing_blocks() -> None:
    dag_source = Path("chartmaster/airflow/dags/daily_market_data_etl.py").read_text(encoding="utf-8")

    assert dag_source.count("catchup=False") == 2
    assert "data_interval_end.in_timezone" in dag_source
    assert "pendulum.now" not in dag_source
    assert "--missing-block-size {MISSING_BLOCK_SIZE}" in dag_source
    assert "--max-missing-blocks {MAX_MISSING_BLOCKS}" in dag_source
