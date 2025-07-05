from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from slack_mcp.slack_app import create_slack_app


def test_e2e_url_verification():
    """Test the end-to-end flow for URL verification."""
    with patch("slack_mcp.slack_app.verify_slack_request", AsyncMock(return_value=True)):
        # Create the FastAPI app and test client
        app = create_slack_app()
        client = TestClient(app)

        # Create a URL verification challenge
        challenge_data = {
            "type": "url_verification",
            "challenge": "test_challenge",
            "token": "test_token",
        }

        # Send the challenge to the endpoint
        response = client.post(
            "/slack/events",
            json=challenge_data,
            headers={"X-Slack-Signature": "valid_sig", "X-Slack-Request-Timestamp": "1234567890"},
        )

        # Verify the response
        assert response.status_code == 200
        assert response.json()["challenge"] == "test_challenge"
