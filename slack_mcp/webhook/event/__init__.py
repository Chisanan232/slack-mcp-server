"""
Slack event consumer package.

This package provides consumer implementations that read Slack events from
various backends and route them to handlers.
"""

from .consumer import SlackEventConsumer
from .handler import BaseSlackEventHandler, DecoratorHandler, EventHandler

__all__ = ["SlackEventConsumer", "BaseSlackEventHandler", "EventHandler", "DecoratorHandler"]
