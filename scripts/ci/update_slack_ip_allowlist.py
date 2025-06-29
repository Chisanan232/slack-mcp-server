#!/usr/bin/env python3
"""
Script to update Slack application IP allowlist with GitHub Actions runner IP ranges.
This script fetches GitHub Actions IP ranges and updates the Slack application's IP allowlist.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from typing import List, Dict, Any, Set


def setup_logger() -> logging.Logger:
    """Set up and configure logger."""
    logger = logging.getLogger("slack-ip-allowlist-updater")
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def get_github_actions_ips() -> List[str]:
    """
    Fetch GitHub Actions IP ranges using curl command.

    Returns:
        List of IP ranges for GitHub Actions
    """
    try:
        # Run the curl command to get GitHub Actions IP ranges
        cmd = "curl -s https://api.github.com/meta | jq -r '.actions[]'"
        result = subprocess.run(cmd, shell=True, check=True, text=True, capture_output=True)
        
        # Split the output by newlines and remove empty lines
        ip_ranges = [ip.strip() for ip in result.stdout.split('\n') if ip.strip()]
        
        return ip_ranges
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to fetch GitHub Actions IP ranges: {e.stderr}")


class SlackAPIClient:
    """Client for interacting with Slack API to manage IP allowlists."""

    def __init__(self, token: str, logger: logging.Logger):
        """
        Initialize Slack API client.

        Args:
            token: Slack application token with admin scopes
            logger: Logger instance
        """
        self.token = token
        self.logger = logger
        
        # Import slack_sdk here to avoid import errors if the script is run
        # without the required dependencies
        try:
            from slack_sdk import WebClient
            from slack_sdk.errors import SlackApiError
            self.WebClient = WebClient
            self.SlackApiError = SlackApiError
        except ImportError:
            self.logger.error("slack_sdk package not found. Please install it using: pip install slack-sdk")
            sys.exit(1)
        
        self.client = self.WebClient(token=self.token)

    def update_ip_allowlist(self, app_id: str, ip_ranges: List[str]) -> bool:
        """
        Update IP allowlist for a Slack application by using Web API directly.
        
        This method handles both getting the current IP allowlist and updating it
        with the new IP ranges.

        Args:
            app_id: Slack application ID
            ip_ranges: List of IP ranges to allow

        Returns:
            True if successful, False otherwise
        """
        try:
            # Format the IP ranges for the Slack API
            formatted_ip_ranges = []
            for idx, ip_range in enumerate(ip_ranges):
                formatted_ip_ranges.append({
                    "cidr": ip_range,
                    "description": f"GitHub Actions runner IP {idx+1}"
                })
            
            # Use the direct API method for setting IP allowlist
            # Method: admin.apps.approved.list is called first to confirm the app exists
            response = self.client.api_call(
                api_method="admin.apps.approved.list",
                params={}
            )
            
            if not response["ok"]:
                self.logger.error(f"Failed to confirm app exists: {response.get('error', 'Unknown error')}")
                return False
                
            # Find the app in the approved list
            app_found = False
            app_name = None
            for app in response.get("approved_apps", []):
                if app.get("app_id") == app_id:
                    app_found = True
                    app_name = app.get("name", "Unknown")
                    break
                    
            if not app_found:
                self.logger.error(f"App ID {app_id} not found in approved apps")
                return False
                
            self.logger.info(f"Found app: {app_name} (ID: {app_id})")
            
            # Now use admin.apps.restrict to update the IP allowlist
            # This method requires app_id and a request_id (we'll use the app_id as request_id)
            response = self.client.api_call(
                api_method="admin.apps.restrict",
                json={
                    "app_id": app_id,
                    "request_id": app_id,
                    "allowed_ip_ranges": formatted_ip_ranges
                }
            )
            
            if response["ok"]:
                self.logger.info(f"Successfully updated IP allowlist for app {app_id}")
                self.logger.info(f"Added {len(ip_ranges)} IP ranges to allowlist")
                return True
            else:
                self.logger.error(f"Failed to update IP allowlist: {response.get('error', 'Unknown error')}")
                return False
                
        except self.SlackApiError as e:
            self.logger.error(f"Failed to update IP allowlist: {e}")
            return False


def main() -> None:
    """Main entry point of the script."""
    logger = setup_logger()
    
    parser = argparse.ArgumentParser(description="Update Slack app IP allowlist with GitHub Actions runner IPs")
    parser.add_argument("--app-id", help="Slack App ID (default: from SLACK_APP_ID env var)",
                        default=os.environ.get("SLACK_APP_ID"))
    parser.add_argument("--token", help="Slack App Token (default: from SLACK_APP_TOKEN env var)",
                        default=os.environ.get("SLACK_APP_TOKEN"))
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Validate token
    if not args.token:
        logger.error("Slack app token not provided. Set SLACK_APP_TOKEN environment variable or use --token")
        sys.exit(1)
        
    # Validate app ID
    if not args.app_id:
        logger.error("Slack app ID not provided. Set SLACK_APP_ID environment variable or use --app-id")
        sys.exit(1)
    
    try:
        # Fetch GitHub Actions IP ranges
        logger.info("Fetching GitHub Actions IP ranges...")
        github_ips = get_github_actions_ips()
        logger.info(f"Found {len(github_ips)} GitHub Actions IP ranges")
        
        # Initialize Slack API client
        slack_client = SlackAPIClient(args.token, logger)
        
        # Update IP allowlist - this will replace all existing entries
        success = slack_client.update_ip_allowlist(args.app_id, github_ips)
        
        if success:
            logger.info("IP allowlist update completed successfully")
            sys.exit(0)
        else:
            logger.error("IP allowlist update failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
