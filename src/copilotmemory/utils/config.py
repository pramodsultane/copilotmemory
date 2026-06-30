"""Configuration management for copilotmemory."""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class ApplicationSettings(BaseSettings):
    """Application configuration settings loaded from environment."""

    # Memory Store Configuration
    memory_db_path: str = "./data/memory.db"
    vector_store_path: str = "./data/vectors"
    embedding_model: str = "all-MiniLM-L6-v2"

    # API Server Configuration
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_log_level: str = "INFO"
    api_workers: int = 4

    # Privacy & Security Settings
    max_memory_size_mb: int = 1000
    auto_cleanup_days: int = 90
    allow_remote_access: bool = False
    enable_encryption: bool = False

    # Performance Tuning
    batch_size: int = 32
    vector_search_top_k: int = 10
    similarity_threshold: float = 0.6
    cache_ttl_seconds: int = 3600

    # Development Settings
    debug: bool = False
    show_sql_queries: bool = False

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def ensure_data_directories(self) -> None:
        """Create necessary data directories if they don't exist."""
        memory_dir = Path(self.memory_db_path).parent
        vector_dir = Path(self.vector_store_path)

        memory_dir.mkdir(parents=True, exist_ok=True)
        vector_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
_settings: Optional[ApplicationSettings] = None


def get_settings() -> ApplicationSettings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = ApplicationSettings()
        _settings.ensure_data_directories()
    return _settings


def reload_settings() -> ApplicationSettings:
    """Reload settings from environment."""
    global _settings
    _settings = ApplicationSettings()
    _settings.ensure_data_directories()
    return _settings
