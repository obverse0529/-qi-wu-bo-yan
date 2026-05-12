from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


def _get_project_root() -> Path:
    """获取项目根目录 (backend/ 目录的父目录)"""
    return Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "启物博言智慧博物馆系统"
    app_version: str = "1.0.0"
    debug: bool = True
    api_prefix: str = "/api/v1"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/qiwu"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/qiwu"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # Milvus
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_collection: str = "artifact_documents"

    # MinIO / S3
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "qiwu-artifacts"
    s3_public_url: str = "http://localhost:9000"

    # LLM - Gemma (Ollama)
    gemma_model_name: str = "gemma3:4b"
    gemma_ollama_base_url: str = "http://localhost:11434"
    gemma_max_length: int = 8192

    # 3D Model - Hunyuan3D
    hunyuan3d_repo_id: str = "tencent/Hunyuan3D-2.1"
    hunyuan3d_path: str = "./Hunyuan3D-2.1"
    hunyuan3d_device: str = "cuda"

    # RAG
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    rag_top_k: int = 5

    # File upload
    upload_max_size_mb: int = 50
    allowed_image_types: list = ["image/jpeg", "image/png", "image/webp"]

    # Paths (computed from project root)
    @property
    def project_root(self) -> Path:
        return _get_project_root()

    @property
    def dataset_dir(self) -> Path:
        return self.project_root / "dataset"

    @property
    def processed_models_dir(self) -> Path:
        return self.dataset_dir / "processed" / "models"

    @property
    def raw_artifacts_dir(self) -> Path:
        return self.dataset_dir / "raw" / "artifacts"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_short: int = 60
    cache_ttl_default: int = 300
    cache_ttl_long: int = 3600

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_default: int = 60
    rate_limit_strict: int = 10
    rate_limit_window: int = 60
    rate_limit_whitelist: list = ["127.0.0.1", "localhost"]

    # Logging
    log_level: str = "INFO"
    log_dir: str = "/app/logs"

    # CORS
    cors_origins: list = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
