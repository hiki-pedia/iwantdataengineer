"""PostgreSQL metadata storage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

import psycopg

from chartmaster.config import Asset, get_postgres_dsn


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS assets (
    symbol TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    market TEXT NOT NULL,
    exchange TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    asset_group TEXT NOT NULL,
    modeling_tier TEXT NOT NULL,
    notes TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id BIGSERIAL PRIMARY KEY,
    pipeline_name TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    message TEXT
);

CREATE TABLE IF NOT EXISTS datasets (
    id BIGSERIAL PRIMARY KEY,
    pipeline_run_id BIGINT REFERENCES pipeline_runs(id),
    dataset_type TEXT NOT NULL,
    provider TEXT,
    symbol TEXT,
    storage_uri TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS model_versions (
    id BIGSERIAL PRIMARY KEY,
    pipeline_run_id BIGINT REFERENCES pipeline_runs(id),
    model_name TEXT NOT NULL,
    version TEXT NOT NULL,
    tier TEXT NOT NULL,
    artifact_uri TEXT NOT NULL,
    train_row_count INTEGER NOT NULL,
    validation_row_count INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (model_name, version)
);

CREATE TABLE IF NOT EXISTS model_metrics (
    id BIGSERIAL PRIMARY KEY,
    model_version_id BIGINT NOT NULL REFERENCES model_versions(id),
    metric_group TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL
);
"""


@dataclass(frozen=True)
class PostgresMetadataStore:
    dsn: str

    @classmethod
    def from_env(cls) -> "PostgresMetadataStore":
        dsn = get_postgres_dsn()
        if not dsn:
            raise ValueError("PostgreSQL DSN is not configured.")
        return cls(dsn)

    def connect(self) -> psycopg.Connection:
        return psycopg.connect(self.dsn)

    def init_schema(self) -> None:
        with self.connect() as connection:
            connection.execute(SCHEMA_SQL)

    def start_pipeline_run(self, pipeline_name: str) -> int:
        with self.connect() as connection:
            row = connection.execute(
                """
                INSERT INTO pipeline_runs (pipeline_name, status, started_at)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (pipeline_name, "running", datetime.now(timezone.utc)),
            ).fetchone()
            return int(row[0])

    def upsert_asset(self, asset: Asset) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO assets (
                    symbol,
                    display_name,
                    market,
                    exchange,
                    asset_type,
                    asset_group,
                    modeling_tier,
                    notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    market = EXCLUDED.market,
                    exchange = EXCLUDED.exchange,
                    asset_type = EXCLUDED.asset_type,
                    asset_group = EXCLUDED.asset_group,
                    modeling_tier = EXCLUDED.modeling_tier,
                    notes = EXCLUDED.notes,
                    updated_at = now()
                """,
                (
                    asset.symbol,
                    asset.display_name,
                    asset.market,
                    asset.exchange,
                    asset.asset_type,
                    asset.group,
                    asset.modeling_tier,
                    asset.notes,
                ),
            )

    def upsert_assets(self, assets: list[Asset]) -> None:
        for asset in assets:
            self.upsert_asset(asset)

    def finish_pipeline_run(self, pipeline_run_id: int, status: str, message: str | None = None) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE pipeline_runs
                SET status = %s, finished_at = %s, message = %s
                WHERE id = %s
                """,
                (status, datetime.now(timezone.utc), message, pipeline_run_id),
            )

    def record_dataset(
        self,
        pipeline_run_id: int,
        dataset_type: str,
        storage_uri: str,
        row_count: int,
        provider: str | None = None,
        symbol: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO datasets (
                    pipeline_run_id,
                    dataset_type,
                    provider,
                    symbol,
                    storage_uri,
                    row_count,
                    start_date,
                    end_date
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (pipeline_run_id, dataset_type, provider, symbol, storage_uri, row_count, start_date, end_date),
            )

    def record_model_version(
        self,
        pipeline_run_id: int,
        model_name: str,
        version: str,
        tier: str,
        artifact_uri: str,
        train_row_count: int,
        validation_row_count: int,
    ) -> int:
        with self.connect() as connection:
            row = connection.execute(
                """
                INSERT INTO model_versions (
                    pipeline_run_id,
                    model_name,
                    version,
                    tier,
                    artifact_uri,
                    train_row_count,
                    validation_row_count
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    pipeline_run_id,
                    model_name,
                    version,
                    tier,
                    artifact_uri,
                    train_row_count,
                    validation_row_count,
                ),
            ).fetchone()
            return int(row[0])

    def record_model_metrics(
        self,
        model_version_id: int,
        metric_group: str,
        metrics: dict[str, float],
    ) -> None:
        rows = [(model_version_id, metric_group, name, value) for name, value in metrics.items()]
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO model_metrics (model_version_id, metric_group, metric_name, metric_value)
                VALUES (%s, %s, %s, %s)
                """,
                rows,
            )
