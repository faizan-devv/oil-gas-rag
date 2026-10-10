from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration, read from CHATBOT_* environment variables or .env."""

    model_config = SettingsConfigDict(
        env_prefix="CHATBOT_", env_file=ROOT / ".env", extra="ignore"
    )

    # Provider names are kept for parity with the deployment env; only the
    # OpenAI-compatible protocol is implemented.
    llm: str = "openai"
    llm_url: str = "http://localhost:8000/v1"
    llm_api_key: str = "changeme"
    llm_model: str = "pucar-llm"

    embedder: str = "openai"
    embed_url: str = "http://localhost:8002/v1"
    embed_api_key: str = "changeme"
    embed_model: str = "bge-m3"
    # TEI rejects requests with more inputs than its max_client_batch_size (32).
    embed_batch_size: int = 32

    data_dir: Path = ROOT / "data" / "raw"
    gold_dir: Path = ROOT / "data" / "gold"
    index_dir: Path = ROOT / "data" / "index"
    output_dir: Path = ROOT / "outputs"

    top_k: int = 5
    # Fuse BM25 keyword ranking with dense retrieval (see README, evaluation).
    hybrid: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
