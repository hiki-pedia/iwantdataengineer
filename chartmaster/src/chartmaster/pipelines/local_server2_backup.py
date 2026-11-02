"""Create and verify ChartMaster file and PostgreSQL backups on server2."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
from dataclasses import dataclass

from chartmaster.config import Server2Config, get_server2_config
from chartmaster.storage.local import SshObjectStorage


BACKUP_DIRECTORIES = ("raw", "curated", "processed", "models", "reports")


@dataclass(frozen=True)
class BackupResult:
    output: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create verified ChartMaster backups on server2.")
    parser.add_argument("--db-container", default=os.environ.get("CHARTMASTER_BACKUP_DB_CONTAINER", "chartmaster-postgres"))
    parser.add_argument("--db-user", default=os.environ.get("CHARTMASTER_BACKUP_DB_USER", "chartmaster"))
    parser.add_argument("--db-name", default=os.environ.get("CHARTMASTER_BACKUP_DB_NAME", "chartmaster"))
    return parser.parse_args()


def build_backup_command(config: Server2Config, db_container: str, db_user: str, db_name: str) -> str:
    base_dir = shlex.quote(config.data_dir)
    container = shlex.quote(db_container)
    user = shlex.quote(db_user)
    database = shlex.quote(db_name)
    directories = " ".join(shlex.quote(directory) for directory in BACKUP_DIRECTORIES)
    return f"""
set -euo pipefail
cd {base_dir}

timestamp="$(date +%Y%m%d_%H%M%S)"
mkdir -p backups/files backups/postgres backups/manifests

file_backup="backups/files/chartmaster_files_${{timestamp}}.tar.gz"
file_manifest="backups/manifests/chartmaster_files_${{timestamp}}.sha256"
db_backup="backups/postgres/chartmaster_metadata_${{timestamp}}_server2.sql.gz"
db_manifest="backups/manifests/chartmaster_metadata_${{timestamp}}_server2.sha256"

tar -czf "$file_backup" {directories}
tar -tzf "$file_backup" >/dev/null
sha256sum "$file_backup" > "$file_manifest"
sha256sum -c "$file_manifest"

docker exec {container} pg_dump -U {user} {database} | gzip > "$db_backup"
test -s "$db_backup"
gzip -t "$db_backup"
sha256sum "$db_backup" > "$db_manifest"
sha256sum -c "$db_manifest"

printf 'timestamp=%s\n' "$timestamp"
printf 'file_backup=%s\n' "$file_backup"
printf 'file_bytes=%s\n' "$(stat -c %s "$file_backup")"
printf 'database_backup=%s\n' "$db_backup"
printf 'database_bytes=%s\n' "$(stat -c %s "$db_backup")"
""".strip()


def create_verified_backup(
    config: Server2Config,
    db_container: str,
    db_user: str,
    db_name: str,
) -> BackupResult:
    storage = SshObjectStorage(config)
    command = build_backup_command(config, db_container, db_user, db_name)
    completed = storage.run_remote(command)
    return BackupResult(output=completed.stdout.decode("utf-8", errors="replace").strip())


def main() -> None:
    args = parse_args()
    config = get_server2_config()
    if config is None:
        raise RuntimeError("Server2 SSH configuration is required for backup.")
    try:
        result = create_verified_backup(config, args.db_container, args.db_user, args.db_name)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip() if exc.stderr else ""
        raise RuntimeError(f"Server2 backup failed: {stderr or exc}") from exc
    print("Server2 backup completed and verified.")
    print(result.output)


if __name__ == "__main__":
    main()
