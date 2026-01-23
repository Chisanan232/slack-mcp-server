from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class TestEnvironment(BaseSettings):
    """
    Test-specific environment settings.
    """

    model_config = SettingsConfigDict(
        env_file="./test/.env.test",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # Test detection
    pytest_current_test: Optional[str] = Field(default=None, alias="PYTEST_CURRENT_TEST")
    ci: bool = Field(default=False, alias="CI")
    github_actions: bool = Field(default=False, alias="GITHUB_ACTIONS")

    # Test configuration
    mcp_no_env_file: bool = Field(default=False, alias="MCP_NO_ENV_FILE")

    # Slack test configuration
    slack_test_channel: Optional[str] = Field(default=None, alias="SLACK_TEST_CHANNEL")
    slack_test_channel_id: Optional[str] = Field(default=None, alias="SLACK_TEST_CHANNEL_ID")

    # End-to-end test credentials
    e2e_test_api_token: Optional[SecretStr] = Field(default=None, alias="E2E_TEST_API_TOKEN")
    slack_events_topic: str = Field(default="slack_events", alias="SLACK_EVENTS_TOPIC")

    @property
    def is_ci_environment(self) -> bool:
        """Check if we're running in a CI environment."""
        return self.ci or self.github_actions


_test_env: Optional[TestEnvironment] = None


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


def is_ci_environment() -> bool:
    """
    Check if we're running in a CI environment.

    Returns
    -------
    bool
        True if running in CI environment
    """
    return get_test_environment().is_ci_environment
