"""Object storage adapters used before AWS S3 is introduced."""

from __future__ import annotations

import io
import pickle
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

import pandas as pd

from chartmaster.config import Server2Config, get_data_dir, get_server2_config


class ObjectStorage(Protocol):
    """Storage interface that can be backed by local files, SSH, or later S3."""

    def write_dataframe_csv(self, dataframe: pd.DataFrame, relative_path: PurePosixPath) -> str:
        """Write a dataframe and return its storage URI."""
        ...

    def read_dataframe_csv(self, relative_path: PurePosixPath) -> pd.DataFrame:
        """Read a dataframe from storage."""
        ...

    def read_dataframe_csv_tail(self, relative_path: PurePosixPath, row_count: int) -> pd.DataFrame:
        """Read the header and the last rows from a CSV file."""
        ...

    def read_text(self, relative_path: PurePosixPath) -> str:
        """Read UTF-8 text from storage."""
        ...

    def write_bytes(self, payload: bytes, relative_path: PurePosixPath) -> str:
        """Write bytes and return their storage URI."""
        ...

    def write_text(self, text: str, relative_path: PurePosixPath) -> str:
        """Write text and return its storage URI."""
        ...


@dataclass(frozen=True)
class LocalObjectStorage:
    base_dir: Path

    def absolute_path(self, relative_path: PurePosixPath) -> Path:
        return self.base_dir / Path(relative_path)

    def uri_for(self, relative_path: PurePosixPath) -> str:
        return str(self.absolute_path(relative_path))

    def write_dataframe_csv(self, dataframe: pd.DataFrame, relative_path: PurePosixPath) -> str:
        path = self.absolute_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        dataframe.to_csv(path, index=False)
        return self.uri_for(relative_path)

    def read_dataframe_csv(self, relative_path: PurePosixPath) -> pd.DataFrame:
        return pd.read_csv(self.absolute_path(relative_path))

    def read_dataframe_csv_tail(self, relative_path: PurePosixPath, row_count: int) -> pd.DataFrame:
        return self.read_dataframe_csv(relative_path).tail(row_count).reset_index(drop=True)

    def read_text(self, relative_path: PurePosixPath) -> str:
        return self.absolute_path(relative_path).read_text(encoding="utf-8")

    def write_bytes(self, payload: bytes, relative_path: PurePosixPath) -> str:
        path = self.absolute_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return self.uri_for(relative_path)

    def write_text(self, text: str, relative_path: PurePosixPath) -> str:
        path = self.absolute_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return self.uri_for(relative_path)


@dataclass(frozen=True)
class SshObjectStorage:
    config: Server2Config

    @property
    def target(self) -> str:
        return f"{self.config.user}@{self.config.host}"

    def remote_path(self, relative_path: PurePosixPath) -> PurePosixPath:
        return PurePosixPath(self.config.data_dir) / relative_path

    def uri_for(self, relative_path: PurePosixPath) -> str:
        return f"ssh://{self.target}{self.remote_path(relative_path)}"

    def ssh_command(self, remote_command: str) -> list[str]:
        command = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "UserKnownHostsFile=/tmp/chartmaster_known_hosts",
        ]
        if self.config.identity_file:
            command += ["-i", str(self.config.identity_file)]
        command += ["-p", str(self.config.port), self.target, remote_command]
        return command

    def run_remote(self, remote_command: str, payload: bytes | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            self.ssh_command(remote_command),
            input=payload,
            capture_output=True,
            check=True,
        )

    def write_dataframe_csv(self, dataframe: pd.DataFrame, relative_path: PurePosixPath) -> str:
        payload = dataframe.to_csv(index=False).encode("utf-8")
        return self.write_bytes(payload, relative_path)

    def read_dataframe_csv(self, relative_path: PurePosixPath) -> pd.DataFrame:
        remote_path = shlex.quote(str(self.remote_path(relative_path)))
        result = self.run_remote(f"cat {remote_path}")
        return pd.read_csv(io.BytesIO(result.stdout))

    def read_dataframe_csv_tail(self, relative_path: PurePosixPath, row_count: int) -> pd.DataFrame:
        if row_count < 1:
            raise ValueError("row_count must be positive")
        remote_path = shlex.quote(str(self.remote_path(relative_path)))
        result = self.run_remote(f"(head -n 1 {remote_path}; tail -n {row_count} {remote_path})")
        return pd.read_csv(io.BytesIO(result.stdout))

    def read_text(self, relative_path: PurePosixPath) -> str:
        remote_path = shlex.quote(str(self.remote_path(relative_path)))
        return self.run_remote(f"cat {remote_path}").stdout.decode("utf-8")

    def write_bytes(self, payload: bytes, relative_path: PurePosixPath) -> str:
        remote_path = self.remote_path(relative_path)
        remote_dir = shlex.quote(str(remote_path.parent))
        remote_file = shlex.quote(str(remote_path))
        self.run_remote(f"mkdir -p {remote_dir} && cat > {remote_file}", payload)
        return self.uri_for(relative_path)

    def write_text(self, text: str, relative_path: PurePosixPath) -> str:
        return self.write_bytes(text.encode("utf-8"), relative_path)


def get_object_storage(local_only: bool = False) -> ObjectStorage:
    """Use server2 SSH storage when configured; otherwise fall back to local files."""
    if local_only:
        return LocalObjectStorage(get_data_dir())
    server2_config = get_server2_config()
    if server2_config:
        return SshObjectStorage(server2_config)
    return LocalObjectStorage(get_data_dir())


def relative_market_raw_path(provider: str, symbol: str) -> PurePosixPath:
    """Return the raw market data relative path for a provider and symbol."""
    return PurePosixPath("raw") / "market_data" / f"provider={provider}" / f"symbol={symbol}" / "data.csv"


def relative_market_features_path(symbol: str) -> PurePosixPath:
    """Return the processed market feature relative path for a symbol."""
    return PurePosixPath("processed") / "features" / f"symbol={symbol}" / "data.csv"


def relative_model_version_dir(model_name: str, version: str) -> PurePosixPath:
    """Return the model artifact relative directory for a model version."""
    return PurePosixPath("models") / model_name / f"version={version}"


def serialize_pickle(payload: object) -> bytes:
    """Serialize an object for model artifact storage."""
    return pickle.dumps(payload)


def write_dataframe_csv(dataframe: pd.DataFrame, path: Path) -> None:
    """Write a dataframe to CSV, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(path, index=False)


def market_raw_path(data_dir: Path, provider: str, symbol: str) -> Path:
    """Return the raw market data path for a provider and symbol."""
    return data_dir / "raw" / "market_data" / f"provider={provider}" / f"symbol={symbol}" / "data.csv"


def market_features_path(data_dir: Path, symbol: str) -> Path:
    """Return the processed market feature path for a symbol."""
    return data_dir / "processed" / "features" / f"symbol={symbol}" / "data.csv"


def model_version_dir(data_dir: Path, model_name: str, version: str) -> Path:
    """Return the local model artifact directory for a model version."""
    return data_dir / "models" / model_name / f"version={version}"
