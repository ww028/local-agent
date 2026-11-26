"""Validated, local-only configuration; paths are relative to the repository."""

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )
    ollama_base_url: str = "http://127.0.0.1:11434"
    llm_model: str = "qwen3:14b"
    embedding_model: str = "bge-m3"
    backend_host: str = "127.0.0.1"
    backend_port: int = Field(default=8000, ge=1024, le=65535)
    frontend_port: int = Field(default=5173, ge=1024, le=65535)
    num_ctx: int = Field(default=8192, ge=2048, le=131072)
    num_predict: int = Field(default=1024, ge=128, le=8192)
    model_timeout_seconds: float = Field(default=180, ge=1, le=1800)
    data_dir: Path = Path("data")
    db_path: Path = Path("data/studio.db")
    lancedb_dir: Path = Path("data/lancedb")
    chunk_size: int = Field(default=600, ge=1)
    chunk_overlap: int = Field(default=120, ge=0)
    terminal_workspace: Path = ROOT
    top_k: int = Field(default=6, ge=1, le=20)

    @field_validator("ollama_base_url")
    @classmethod
    def local_url(cls, value: str) -> str:
        url = urlparse(value)
        if (
            url.scheme != "http"
            or url.hostname not in {"localhost", "127.0.0.1", "::1"}
            or url.username
            or url.password
            or url.query
            or url.fragment
            or url.path not in {"", "/"}
        ):
            raise ValueError("Ollama must use an HTTP loopback URL without credentials.")
        return value.rstrip("/")

    @field_validator("backend_host")
    @classmethod
    def local_host(cls, value: str) -> str:
        if value not in {"127.0.0.1", "::1", "localhost"}:
            raise ValueError("This single-user build only binds to loopback.")
        return value

    @field_validator("data_dir", "db_path", "lancedb_dir")
    @classmethod
    def resolve_path(cls, value: Path) -> Path:
        return value if value.is_absolute() else ROOT / value

    @field_validator("terminal_workspace")
    @classmethod
    def terminal_root(cls, value: Path) -> Path:
        value = value if value.is_absolute() else ROOT / value
        from app.terminal.catalog import workspace_path

        return workspace_path(value)

    @model_validator(mode="after")
    def budgets(self) -> "Settings":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE.")
        if self.num_predict + 1024 >= self.num_ctx:
            raise ValueError("NUM_CTX must leave space for input and output.")
        return self

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
