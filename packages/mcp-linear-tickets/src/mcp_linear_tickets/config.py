"""Configuration for the MCP Linear Tickets server."""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for the MCP Linear Tickets server."""

    linear_api_key: str
    groq_api_key: str
    linear_team_id: Optional[str] = None

    # FastMCP settings
    server_name: str = "linear"

    # Linear API settings
    linear_api_url: str = "https://api.linear.app/graphql"

    # Groq settings
    groq_model: str = "llama-3.3-70b-versatile"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
