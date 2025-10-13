"""Centralized logging configuration for tests.

This module provides test-specific logging configuration to ensure
consistent and clean logging behavior during test execution.
"""

import logging
import logging.config
import os
from typing import Optional

# Default test log level - higher than INFO to reduce noise
DEFAULT_TEST_LOG_LEVEL = "WARNING"


def setup_test_logging(level: Optional[str] = None, verbose: bool = False) -> None:
    """Configure logging for test execution.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               If None, uses DEFAULT_TEST_LOG_LEVEL or TEST_LOG_LEVEL env var.
        verbose: If True, enables more verbose logging (INFO level).
    """
    # Determine log level
    if level is None:
        if verbose:
            level = "INFO"
        else:
            level = os.getenv("TEST_LOG_LEVEL", DEFAULT_TEST_LOG_LEVEL)
    
    level = level.upper()

    # Simple test logging configuration
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {
                "format": "%(levelname)s - %(name)s - %(message)s",
            },
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
                "datefmt": "%H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "simple" if not verbose else "detailed",
                "stream": "ext://sys.stdout",
                "level": level,
            }
        },
        "loggers": {
            "": {  # root logger
                "handlers": ["console"],
                "level": level,
                "propagate": False,
            },
            "slack_mcp": {
                "handlers": ["console"],
                "level": level,
                "propagate": False,
            },
            # Reduce noise from external libraries
            "uvicorn": {
                "handlers": ["console"],
                "level": "ERROR",
                "propagate": False,
            },
            "httpx": {
                "handlers": ["console"],
                "level": "ERROR",
                "propagate": False,
            },
            "asyncio": {
                "handlers": ["console"],
                "level": "ERROR",
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(logging_config)


def get_test_logger(name: str) -> logging.Logger:
    """Get a logger for test code.

    Args:
        name: Name of the logger (typically __name__).

    Returns:
        logging.Logger: Configured test logger.
    """
    return logging.getLogger(name)