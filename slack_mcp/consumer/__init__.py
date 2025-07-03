"""
Slack event consumer package.

This package provides consumer implementations that read Slack events from
various backends and route them to handlers.
"""

from .slack_event import SlackEventConsumer

__all__ = ["SlackEventConsumer"]
