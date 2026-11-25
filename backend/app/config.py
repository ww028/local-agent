"""Application configuration.

All settings are read from environment variables (see ``.env.example``).
No value is hard-coded here so the same code can run across local, staging
and production-like environments.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen3:14b"
    embedding_model: str = "bge-m3"

    # Backend
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    num_ctx: int = 8192

    # Frontend
    frontend_port: int = 5173

    # Storage
    data_dir: Path = Path("./data")
    db_path: Path = Path("./data/studio.db")
    lancedb_dir: Path = Path("./data/lancedb")

    # RAG tuning
    chunk_size: int = 600
    chunk_overlap: int = 120
    top_k: int = 6

    def ensure_dirs(self) -> None:
        """Create local storage directories if missing."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.lancedb_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
