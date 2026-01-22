"""Centralized logging configuration for Slack MCP Server.

This module provides a centralized way to configure logging for the application.
It supports both programmatic configuration and command-line integration.
"""

import logging
import logging.config
import os
from pathlib import Path
from typing import Any, Dict, Optional

from slack_mcp.settings import get_settings

# Default log format
DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)8s] %(name)s: %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Default log levels
DEFAULT_LEVEL = "INFO"
LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Log file configuration
DEFAULT_LOG_DIR = "logs"
DEFAULT_LOG_FILE = "slack_mcp.log"


def get_log_file_path(log_dir: Optional[str] = None, log_file: Optional[str] = None) -> str:
    """Get the full path to the log file.

    Args:
        log_dir: Directory to store log files. If None, uses DEFAULT_LOG_DIR.
        log_file: Name of the log file. If None, uses DEFAULT_LOG_FILE.

    Returns:
        str: Full path to the log file.
    """
    log_dir = log_dir or DEFAULT_LOG_DIR
    log_file = log_file or DEFAULT_LOG_FILE

    # Create log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    return str(Path(log_dir) / log_file)


def get_logging_config(
    level: str = DEFAULT_LEVEL,
    log_file: Optional[str] = None,
    log_format: str = DEFAULT_LOG_FORMAT,
    date_format: str = DEFAULT_DATE_FORMAT,
) -> Dict[str, Any]:
    """Get the logging configuration dictionary.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Path to log file. If None, logs to console only.
        log_format: Log message format string.
        date_format: Date format string for log messages.

    Returns:
        Dict containing the logging configuration.
    """
    # Convert level to uppercase and validate
    level = level.upper()
    if level not in LOG_LEVELS:
        level = DEFAULT_LEVEL

    # Base formatters
    formatters = {
        "default": {
            "format": log_format,
            "datefmt": date_format,
            "style": "%",
        },
    }

    # Add JSON formatter only if pythonjsonlogger is available
    try:
        import pythonjsonlogger.jsonlogger  # noqa: F401

        formatters["json"] = {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            "datefmt": date_format,
        }
    except ImportError:
        # pythonjsonlogger not available, skip JSON formatter
        pass

    # Base handlers
    handlers: Dict[str, Dict[str, Any]] = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
            "level": level,
        }
    }

    # Add file handler if log_file is provided
    if log_file:
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "default",
            "filename": log_file,
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "encoding": "utf8",
            "level": level,
        }

    # Configure root logger and all other loggers
    loggers = {
        "": {  # root logger
            "handlers": list(handlers.keys()),
            "level": level,
            "propagate": False,
        },
        "slack_mcp": {
            "handlers": list(handlers.keys()),
            "level": level,
            "propagate": False,
        },
        "uvicorn": {
            "handlers": list(handlers.keys()),
            "level": "WARNING",  # Reduce uvicorn log noise
            "propagate": False,
        },
        "httpx": {
            "handlers": list(handlers.keys()),
            "level": "WARNING",  # Reduce httpx log noise
            "propagate": False,
        },
    }

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "loggers": loggers,
    }


def setup_logging(
    level: str = DEFAULT_LEVEL,
    log_file: Optional[str] = None,
    log_format: str = DEFAULT_LOG_FORMAT,
    date_format: str = DEFAULT_DATE_FORMAT,
) -> None:
    """Configure logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Path to log file. If None, logs to console only.
        log_format: Log message format string.
        date_format: Date format string for log messages.
    """
    config = get_logging_config(
        level=level,
        log_file=log_file,
        log_format=log_format,
        date_format=date_format,
    )
    logging.config.dictConfig(config)

    # Set asyncio logger level to WARNING to reduce noise
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)


def add_logging_arguments(parser):
    """Add logging-related command line arguments to an argument parser.

    Args:
        parser: Argument parser to add logging options to.
    """
    # Get settings for defaults
    settings = get_settings()
    
    log_group = parser.add_argument_group("Logging Options")

    log_group.add_argument(
        "--log-level",
        dest="log_level",
        type=str.upper,
        default=settings.log_level,
        choices=LOG_LEVELS,
        help=f"Set the logging level (default: {settings.log_level})",
    )

    log_group.add_argument(
        "--log-file",
        dest="log_file",
        default=settings.log_file,
        help="Path to log file. If not set, logs to console only.",
    )

    log_group.add_argument(
        "--log-dir",
        dest="log_dir",
        default=settings.log_dir,
        help=f"Directory to store log files (default: {settings.log_dir})",
    )

    log_group.add_argument(
        "--log-format",
        dest="log_format",
        default=settings.log_format,
        help=f"Log message format (default: '{settings.log_format}')",
    )

    return parser


def setup_logging_from_args(args):
    """Set up logging from command-line arguments.

    Args:
        args: Parsed command-line arguments (from add_logging_arguments).
    """
    log_file = None
    if hasattr(args, "log_file") and args.log_file:
        log_file = args.log_file
    elif hasattr(args, "log_dir") and args.log_dir:
        log_file = get_log_file_path(args.log_dir)

    setup_logging(
        level=getattr(args, "log_level", DEFAULT_LEVEL),
        log_file=log_file,
        log_format=getattr(args, "log_format", DEFAULT_LOG_FORMAT),
    )
