from typing import Optional
from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class SettingModel(BaseSettings):
    """
    Configuration model for the Slack MCP server.
    Loads values from environment variables or a .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # Slack API credentials
    slack_bot_id: Optional[str] = Field(default=None, alias="SLACK_BOT_ID")
    slack_app_id: Optional[str] = Field(default=None, alias="SLACK_APP_ID")
    slack_bot_token: Optional[SecretStr] = Field(
        default=None, validation_alias=AliasChoices("SLACK_BOT_TOKEN", "SLACK_TOKEN")
    )
    slack_user_token: Optional[SecretStr] = Field(default=None, alias="SLACK_USER_TOKEN")
    slack_signing_secret: Optional[SecretStr] = Field(default=None, alias="SLACK_SIGNING_SECRET")

    # Slack test configuration
    slack_test_channel: Optional[str] = Field(default=None, alias="SLACK_TEST_CHANNEL")
    slack_test_channel_id: Optional[str] = Field(default=None, alias="SLACK_TEST_CHANNEL_ID")

    # End-to-end test credentials
    e2e_test_api_token: Optional[SecretStr] = Field(default=None, alias="E2E_TEST_API_TOKEN")

    # Message queue backend settings
    queue_backend: str = Field(default="memory", alias="QUEUE_BACKEND")
    redis_url: Optional[str] = Field(default=None, alias="REDIS_URL")
    kafka_bootstrap: Optional[str] = Field(default=None, alias="KAFKA_BOOTSTRAP")
    slack_events_topic: str = Field(default="slack_events", alias="SLACK_EVENTS_TOPIC")

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
    
    # Check if we should skip .env loading based on environment variable (useful for tests)
    import os
    if os.environ.get("MCP_NO_ENV_FILE", "").lower() == "true":
        no_env_file = True
        
    if _settings is None or force_reload:
        actual_env_file = None if no_env_file else env_file
        _settings = SettingModel(_env_file=actual_env_file, **kwargs)
    return _settings
