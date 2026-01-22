from typing import Optional
from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class TestEnvironment(BaseSettings):
    """
    Test-specific environment settings.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env.test",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )
    
    # Test detection
    pytest_current_test: Optional[str] = Field(default=None, alias="PYTEST_CURRENT_TEST")
    ci: Optional[str] = Field(default=None, alias="CI")
    github_actions: Optional[str] = Field(default=None, alias="GITHUB_ACTIONS")
    
    # Test configuration
    mcp_no_env_file: bool = Field(default=False, alias="MCP_NO_ENV_FILE")
    slack_events_topic: str = Field(default="slack_events", alias="SLACK_EVENTS_TOPIC")
    
    @property
    def is_test_environment(self) -> bool:
        """Check if we're running in a test environment."""
        return self.pytest_current_test is not None
    
    @property
    def is_ci_environment(self) -> bool:
        """Check if we're running in a CI environment."""
        return (
            (self.ci and self.ci.lower() == "true") or
            (self.github_actions and self.github_actions.lower() == "true")
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
        default=None, validation_alias=AliasChoices("SLACK_BOT_TOKEN", "SLACK_TOKEN", "E2E_TEST_API_TOKEN")
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

    # Logging settings
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, alias="LOG_FILE")
    log_dir: str = Field(default="logs", alias="LOG_DIR")
    log_format: str = Field(default="%(asctime)s [%(levelname)8s] %(name)s: %(message)s", alias="LOG_FORMAT")

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
_test_env: Optional[TestEnvironment] = None


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
    
    # Check if we should skip .env loading based on test environment settings
    test_env = get_test_environment()
    if test_env.mcp_no_env_file:
        no_env_file = True
        
    if _settings is None or force_reload:
        actual_env_file = None if no_env_file else env_file
        _settings = SettingModel(_env_file=actual_env_file, **kwargs)
    return _settings


def get_test_environment(force_reload: bool = False) -> TestEnvironment:
    """
    Get the test environment settings instance.

    Parameters
    ----------
    force_reload : bool, optional
        Whether to force a reload of the test environment settings, by default False

    Returns
    -------
    TestEnvironment
        The test environment settings instance
    """
    global _test_env
    
    if _test_env is None or force_reload:
        _test_env = TestEnvironment()
    return _test_env


def is_test_environment() -> bool:
    """
    Check if we're running in a test environment.
    
    Returns
    -------
    bool
        True if running in test environment
    """
    return get_test_environment().is_test_environment


def is_ci_environment() -> bool:
    """
    Check if we're running in a CI environment.
    
    Returns
    -------
    bool
        True if running in CI environment
    """
    return get_test_environment().is_ci_environment
