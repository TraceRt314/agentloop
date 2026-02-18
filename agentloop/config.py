"""Configuration management for AgentLoop."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="AGENTLOOP_"
    )
    
    # Database
    database_url: str = "sqlite:///./agentloop.db"
    
    # API
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    debug: bool = False
    
    # OpenClaw Integration
    openclaw_base_url: str = "http://localhost:3000"
    openclaw_token: str = ""
    
    # Agent defaults
    agent_work_interval_seconds: int = 300  # 5 minutes
    orchestrator_tick_interval_seconds: int = 300  # 5 minutes
    
    # Projects and agents directories
    agents_dir: str = "./agents"
    projects_dir: str = "./projects"
    
    # Logging
    log_level: str = "INFO"


# Global settings instance
settings = Settings()