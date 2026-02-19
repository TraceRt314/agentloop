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
    api_port: int = 8080
    api_base_url: str = "http://localhost:8080"
    debug: bool = True

    # OpenClaw Gateway
    openclaw_gateway_url: str = "ws://localhost:18789"
    openclaw_gateway_token: str = ""

    # Mission Control
    mc_base_url: str = "http://localhost:8002"
    mc_token: str = ""
    mc_org_id: str = ""
    board_map: str = "{}"

    # Agent defaults
    agent_work_interval_seconds: int = 300
    orchestrator_tick_interval_seconds: int = 300

    # Step execution
    step_timeout_seconds: int = 300

    # Projects and agents directories
    agents_dir: str = "./agents"
    projects_dir: str = "./projects"

    # Logging
    log_level: str = "INFO"


# Global settings instance
settings = Settings()
