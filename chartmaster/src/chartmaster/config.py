"""Project-level configuration helpers."""

import json
import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_ROOT.parent
ASSET_REGISTRY_PATH = PROJECT_ROOT / "config" / "assets.json"
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_SERVER2_RELATIVE_DATA_DIR = "iwantdataengineer/chartmaster"


def load_env_files() -> None:
    """Load .env files without relying on shell source syntax."""
    for path in (REPO_ROOT / ".env", PROJECT_ROOT / ".env"):
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


load_env_files()


@dataclass(frozen=True)
class Asset:
    symbol: str
    display_name: str
    market: str
    exchange: str
    asset_type: str
    group: str
    modeling_tier: str
    notes: str


def get_data_dir() -> Path:
    """Return the local data directory, overridable for server2-mounted storage."""
    return Path(os.environ.get("CHARTMASTER_DATA_DIR", DEFAULT_DATA_DIR)).expanduser()


def load_assets(path: Path = ASSET_REGISTRY_PATH) -> list[Asset]:
    """Load the asset registry from JSON."""
    with path.open("r", encoding="utf-8") as file:
        rows = json.load(file)
    return [Asset(**row) for row in rows]


@dataclass(frozen=True)
class Server2Config:
    host: str
    user: str
    port: int
    identity_file: Path | None
    data_dir: str


def get_server2_config() -> Server2Config | None:
    """Return server2 SSH configuration when available."""
    host = os.environ.get("CHARTMASTER_SERVER2_HOST")
    user = os.environ.get("CHARTMASTER_SERVER2_USER")
    if not host or not user:
        return None

    identity_value = os.environ.get("CHARTMASTER_SERVER2_IDENTITY_FILE")
    identity_file = Path(identity_value).expanduser() if identity_value else None
    data_dir = os.environ.get("CHARTMASTER_SERVER2_DATA_DIR") or f"/home/{user}/{DEFAULT_SERVER2_RELATIVE_DATA_DIR}"
    return Server2Config(
        host=host,
        user=user,
        port=int(os.environ.get("CHARTMASTER_SERVER2_PORT", "22")),
        identity_file=identity_file,
        data_dir=data_dir,
    )


def get_postgres_dsn() -> str | None:
    """Return the PostgreSQL DSN, preferring the explicit libpq DSN."""
    explicit_dsn = os.environ.get("CHARTMASTER_POSTGRES_DSN")
    if explicit_dsn:
        return explicit_dsn

    host = os.environ.get("CHARTMASTER_DB_HOST")
    port = os.environ.get("CHARTMASTER_DB_PORT")
    dbname = os.environ.get("CHARTMASTER_DB_NAME")
    user = os.environ.get("CHARTMASTER_DB_USER")
    password = os.environ.get("CHARTMASTER_DB_PASSWORD")
    if not all([host, port, dbname, user]):
        return None

    dsn_parts = [
        f"dbname={dbname}",
        f"user={user}",
        f"host={host}",
        f"port={port}",
    ]
    if password:
        dsn_parts.append(f"password={password}")
    return " ".join(dsn_parts)
