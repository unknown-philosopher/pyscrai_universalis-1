"""
Configuration module for PyScrAI Universalis.

Centralizes configuration management and environment variable handling.
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class DatabaseConfig:
    """MongoDB configuration."""
    uri: str = field(default_factory=lambda: os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
    db_name: str = field(default_factory=lambda: os.getenv("MONGO_DB_NAME", "universalis_mongodb"))
    

@dataclass
class ChromaDBConfig:
    """ChromaDB configuration."""
    host: str = field(default_factory=lambda: os.getenv("CHROMA_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("CHROMA_PORT", "8000")))
    collection_name: str = field(default_factory=lambda: os.getenv("CHROMA_COLLECTION", "pyscrai_memories"))
    persist_directory: Optional[str] = field(default_factory=lambda: os.getenv("CHROMA_PERSIST_DIR", None))
    use_http: bool = field(default_factory=lambda: os.getenv("CHROMA_USE_HTTP", "true").lower() == "true")


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    api_key: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    base_url: str = field(default_factory=lambda: os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"))
    model_name: str = field(default_factory=lambda: os.getenv("MODEL_NAME", "xiaomi/mimo-v2-flash:free"))
    temperature: float = field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.7")))


@dataclass
class LangfuseConfig:
    """Langfuse observability configuration."""
    public_key: str = field(default_factory=lambda: os.getenv("LANGFUSE_PUBLIC_KEY", ""))
    secret_key: str = field(default_factory=lambda: os.getenv("LANGFUSE_SECRET_KEY", ""))
    host: str = field(default_factory=lambda: os.getenv("LANGFUSE_HOST", "http://localhost:3000"))
    enabled: bool = field(default_factory=lambda: os.getenv("LANGFUSE_ENABLED", "true").lower() == "true")


@dataclass
class ServerConfig:
    """API server configuration."""
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))


@dataclass
class PyScrAIConfig:
    """Main configuration class for PyScrAI Universalis."""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    chromadb: ChromaDBConfig = field(default_factory=ChromaDBConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    langfuse: LangfuseConfig = field(default_factory=LangfuseConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    simulation_id: str = field(default_factory=lambda: os.getenv("SIMULATION_ID", "Alpha_Scenario"))


# Global configuration instance
config = PyScrAIConfig()


def get_config() -> PyScrAIConfig:
    """Get the global configuration instance."""
    return config


def reload_config() -> PyScrAIConfig:
    """Reload configuration from environment variables."""
    global config
    load_dotenv(override=True)
    config = PyScrAIConfig()
    return config

