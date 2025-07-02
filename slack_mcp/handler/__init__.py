"""
Slack event handler package.

This package provides different styles of Slack event handling:
1. OO-style (inheritance-based)
2. Decorator-style with enum arguments
3. Decorator-style with attribute access
"""

from .base import BaseSlackEventHandler

__all__ = ["BaseSlackEventHandler"]
