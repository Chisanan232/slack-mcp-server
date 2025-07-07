"""
Slack event consumer package.

This package provides consumer implementations that read Slack events from
various backends and route them to handlers.
"""

from .consumer import SlackEventConsumer
from .handler import BaseSlackEventHandler, EventHandler
from .handler import DecoratorHandler

__all__ = ["SlackEventConsumer", "BaseSlackEventHandler", "EventHandler", "DecoratorHandler"]
