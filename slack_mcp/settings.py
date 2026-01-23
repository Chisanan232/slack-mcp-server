from enum import Enum
from typing import Optional

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class QueueBackend(str, Enum):
    """Supported message queue backends."""

    MEMORY = "memory"
    REDIS = "redis"
    KAFKA = "kafka"


class LogLevel(str, Enum):
    """Supported logging levels."""

    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"
    NOTSET = "NOTSET"


class SettingModel(BaseSettings):
    """
    Configuration model for the Slack MCP server.
    Loads values from environment variables or a .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Slack API credentials
    slack_bot_id: Optional[str] = Field(default=None)
    slack_app_id: Optional[str] = Field(default=None)
    slack_bot_token: Optional[SecretStr] = Field(
        default=None, validation_alias=AliasChoices("SLACK_BOT_TOKEN", "SLACK_TOKEN", "E2E_TEST_API_TOKEN")
    )
    slack_user_token: Optional[SecretStr] = Field(default=None)
    slack_signing_secret: Optional[SecretStr] = Field(default=None)

    # Message queue backend settings
    queue_backend: QueueBackend = Field(default=QueueBackend.MEMORY)
    redis_url: Optional[str] = Field(default=None)
    kafka_bootstrap: Optional[str] = Field(default=None)
    slack_events_topic: str = Field(default="slack_events")

    # Logging settings
    log_level: LogLevel = Field(default=LogLevel.INFO)
    log_file: Optional[str] = Field(default=None)
    log_dir: str = Field(default="logs")
    log_format: str = Field(default="%(asctime)s [%(levelname)8s] %(name)s: %(message)s")

    # Web server CORS settings
    cors_allow_origins: str = Field(default="*")
    cors_allow_credentials: bool = Field(default=True)
    cors_allow_methods: str = Field(default="*")
    cors_allow_headers: str = Field(default="*")

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string."""
        if isinstance(v, str):
            # Handle empty string
            if not v.strip():
                return "*"
            return v.strip()
        return v or "*"

    @field_validator("cors_allow_methods", mode="before")
    @classmethod
    def parse_cors_methods(cls, v):
        """Parse CORS methods from string."""
        if isinstance(v, str):
            # Handle empty string
            if not v.strip():
                return "*"
            return v.strip()
        return v or "*"

    @field_validator("cors_allow_headers", mode="before")
    @classmethod
    def parse_cors_headers(cls, v):
        """Parse CORS headers from string."""
        if isinstance(v, str):
            # Handle empty string
            if not v.strip():
                return "*"
            return v.strip()
        return v or "*"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """
        Customize the settings sources to prioritize .env file over environment variables.
        This matches the previous behavior of load_dotenv(override=True).
        """
        return init_settings, dotenv_settings, env_settings, file_secret_settings


_settings: Optional[SettingModel] = None


def get_settings(
    env_file: Optional[str] = ".env", no_env_file: bool = False, force_reload: bool = False, **kwargs
) -> SettingModel:
    """
    Get the global settings instance.

    Parameters
    ----------
    env_file : Optional[str], optional
        Path to the .env file, by default ".env"
    no_env_file : bool, optional
        Whether to skip loading the .env file, by default False
    force_reload : bool, optional
        Whether to force a reload of the settings, by default False
    **kwargs
        Additional settings to override

    Returns
    -------
    SettingModel
        The settings instance
    """
    global _settings

    if _settings is None or force_reload:
        actual_env_file = None if no_env_file else env_file
        _settings = SettingModel(_env_file=actual_env_file, **kwargs)
    return _settings
