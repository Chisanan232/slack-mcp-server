"""Common utilities for E2E tests."""

from slack_mcp.settings import get_settings


def should_run_e2e_tests() -> bool:
    """Check if E2E tests should run based on available credentials.

    Returns
    -------
    bool
        True if both E2E_TEST_API_TOKEN and SLACK_TEST_CHANNEL_ID are available
    """
    settings = get_settings()
    has_token = bool(settings.e2e_test_api_token and settings.e2e_test_api_token.get_secret_value())
    has_channel = bool(settings.slack_test_channel_id)
    return has_token and has_channel


def get_e2e_credentials():
    """Get E2E test credentials from settings.

    Returns
    -------
    tuple[str, str]
        Tuple of (bot_token, channel_id)

    Raises
    ------
    ValueError
        If credentials are not available
    """
    settings = get_settings()
    bot_token = settings.e2e_test_api_token.get_secret_value() if settings.e2e_test_api_token else None
    channel_id = settings.slack_test_channel_id

    if not bot_token:
        raise ValueError("E2E_TEST_API_TOKEN not set in settings")
    if not channel_id:
        raise ValueError("SLACK_TEST_CHANNEL_ID not set in settings")

    return bot_token, channel_id
