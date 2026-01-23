"""Common utilities for E2E tests."""

from test.settings import get_test_environment


def should_run_e2e_tests() -> bool:
    """Check if E2E tests should run based on available credentials.

    Returns
    -------
    bool
        True if both E2E_TEST_API_TOKEN and SLACK_TEST_CHANNEL_ID are available
    """
    test_env = get_test_environment()
    has_token = bool(test_env.e2e_test_api_token and test_env.e2e_test_api_token.get_secret_value())
    has_channel = bool(test_env.slack_test_channel_id)
    return has_token and has_channel


def get_e2e_credentials():
    """Get E2E test credentials from test environment.

    Returns
    -------
    tuple[str, str]
        Tuple of (bot_token, channel_id)

    Raises
    ------
    ValueError
        If credentials are not available
    """
    test_env = get_test_environment()
    bot_token = test_env.e2e_test_api_token.get_secret_value() if test_env.e2e_test_api_token else None
    channel_id = test_env.slack_test_channel_id

    if not bot_token:
        raise ValueError("E2E_TEST_API_TOKEN not set in test environment")
    if not channel_id:
        raise ValueError("SLACK_TEST_CHANNEL_ID not set in test environment")

    return bot_token, channel_id
