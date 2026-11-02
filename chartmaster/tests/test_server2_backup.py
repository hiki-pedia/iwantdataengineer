from pathlib import Path

from chartmaster.config import Server2Config
from chartmaster.pipelines.local_server2_backup import BACKUP_DIRECTORIES, build_backup_command


def test_backup_command_covers_files_database_and_integrity_checks() -> None:
    config = Server2Config(
        host="server2",
        user="chartmaster",
        port=22,
        identity_file=None,
        data_dir="/srv/chartmaster data",
    )

    command = build_backup_command(config, "chartmaster-postgres", "chartmaster", "chartmaster")

    assert "cd '/srv/chartmaster data'" in command
    assert all(directory in command for directory in BACKUP_DIRECTORIES)
    assert "tar -tzf" in command
    assert "pg_dump -U chartmaster chartmaster" in command
    assert "gzip -t" in command
    assert command.count("sha256sum -c") == 2


def test_weekly_backup_dag_schedule_and_safety_settings() -> None:
    source = Path("chartmaster/airflow/dags/weekly_backup.py").read_text(encoding="utf-8")

    assert 'dag_id="weekly_chartmaster_backup"' in source
    assert 'schedule="0 3 * * 0"' in source
    assert "catchup=False" in source
    assert 'task_id="backup_and_verify_server2"' in source
    assert "local_server2_backup" in source
