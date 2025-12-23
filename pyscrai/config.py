"""
Configuration module for PyScrAI Universalis (GeoScrAI).

Centralizes configuration management and environment variable handling.
Uses DuckDB for physical state and LanceDB for semantic memory.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class DuckDBConfig:
    """DuckDB configuration for physical state storage."""
    path: str = field(
        default_factory=lambda: os.getenv(
            "DUCKDB_PATH", 
            str(Path(__file__).parent / "database" / "geoscrai.duckdb")
        )
    )
    read_only: bool = field(
        default_factory=lambda: os.getenv("DUCKDB_READ_ONLY", "false").lower() == "true"
    )
    # Spatial extension is loaded automatically
    enable_spatial: bool = True


@dataclass
class LanceDBConfig:
    """LanceDB configuration for semantic memory."""
    path: str = field(
        default_factory=lambda: os.getenv(
            "LANCEDB_PATH",
            str(Path(__file__).parent / "database" / "lancedb")
        )
    )
    table_name: str = field(
        default_factory=lambda: os.getenv("LANCEDB_TABLE", "memories")
    )
    embedding_dim: int = field(
        default_factory=lambda: int(os.getenv("LANCEDB_EMBEDDING_DIM", "384"))
    )


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    api_key: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    base_url: str = field(default_factory=lambda: os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"))
    model_name: str = field(default_factory=lambda: os.getenv("MODEL_NAME", "xiaomi/mimo-v2-flash:free"))
    temperature: float = field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.7")))
    embedding_model: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    )


@dataclass
class LangfuseConfig:
    """Langfuse observability configuration."""
    public_key: str = field(default_factory=lambda: os.getenv("LANGFUSE_PUBLIC_KEY", ""))
    secret_key: str = field(default_factory=lambda: os.getenv("LANGFUSE_SECRET_KEY", ""))
    host: str = field(default_factory=lambda: os.getenv("LANGFUSE_HOST", "http://localhost:3000"))
    enabled: bool = field(default_factory=lambda: os.getenv("LANGFUSE_ENABLED", "true").lower() == "true")


@dataclass
class UIConfig:
    """NiceGUI configuration."""
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8080")))
    title: str = field(default_factory=lambda: os.getenv("UI_TITLE", "GeoScrAI Universalis"))
    dark_mode: bool = field(default_factory=lambda: os.getenv("UI_DARK_MODE", "true").lower() == "true")
    reload: bool = field(default_factory=lambda: os.getenv("UI_RELOAD", "false").lower() == "true")


@dataclass
class SimulationConfig:
    """Simulation-specific configuration."""
    simulation_id: str = field(default_factory=lambda: os.getenv("SIMULATION_ID", "Alpha_Scenario"))
    tick_interval_ms: int = field(
        default_factory=lambda: int(os.getenv("TICK_INTERVAL_MS", "1000"))
    )
    auto_run: bool = field(
        default_factory=lambda: os.getenv("AUTO_RUN", "false").lower() == "true"
    )
    perception_radius_degrees: float = field(
        default_factory=lambda: float(os.getenv("PERCEPTION_RADIUS", "0.1"))  # ~11km
    )


@dataclass
class PyScrAIConfig:
    """Main configuration class for PyScrAI Universalis (GeoScrAI)."""
    duckdb: DuckDBConfig = field(default_factory=DuckDBConfig)
    lancedb: LanceDBConfig = field(default_factory=LanceDBConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    langfuse: LangfuseConfig = field(default_factory=LangfuseConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    
    def ensure_directories(self) -> None:
        """Ensure database directories exist."""
        Path(self.duckdb.path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.lancedb.path).mkdir(parents=True, exist_ok=True)


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
