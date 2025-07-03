"""
Handler implementations for Slack events.

This package contains the handler interfaces and implementations for Slack events.
The base module provides a class-based handler pattern that maps event types to methods.
"""

from __future__ import annotations

from .base import BaseSlackEventHandler, EventHandler
from .decorator import DecoratorHandler

__all__ = ["BaseSlackEventHandler", "EventHandler", "DecoratorHandler"]
