"""Utility functions for handling Slack API retries."""

import asyncio
import functools
import logging
import random
from typing import Any, Awaitable, Callable, TypeVar

from slack_sdk.errors import SlackApiError

# Set up logging
logger = logging.getLogger("slack_retry_utils")

# Type variables for decorator
T = TypeVar("T")
R = TypeVar("R")


def with_slack_retry(
    max_retries: int = 3,
    initial_delay: float = 5.0,
    backoff_factor: float = 2.0,
    jitter: float = 0.1,
) -> Callable[[Callable[..., Awaitable[R]]], Callable[..., Awaitable[R]]]:
    """
    Decorator that retries a Slack API call when rate limits (HTTP 429) are hit.

    Args:
        max_retries: Maximum number of retries before giving up
        initial_delay: Initial delay in seconds before first retry
        backoff_factor: Multiplicative factor for increasing delay between retries
        jitter: Random factor to add to delay to prevent thundering herd

    Returns:
        Decorated function that handles retries
    """

    def decorator(func: Callable[..., Awaitable[R]]) -> Callable[..., Awaitable[R]]:
        @functools.wraps(func)
        async def wrapper_async(*args: Any, **kwargs: Any) -> R:
            last_exception = None
            delay = initial_delay

            # Try the call up to max_retries + 1 times (initial + retries)
            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        logger.warning(f"Retry attempt {attempt} of {max_retries} for {func.__name__}")

                    return await func(*args, **kwargs)

                except SlackApiError as e:
                    last_exception = e

                    # Check if this is a rate limit error (HTTP 429)
                    if e.response and e.response.status_code == 429:
                        if attempt < max_retries:
                            # Get retry time from headers or use our calculated delay
                            retry_after = int(e.response.headers.get("Retry-After", delay))

                            # Add some jitter to avoid all clients hitting at once
                            jitter_amount = random.uniform(-jitter, jitter) * retry_after
                            sleep_time = retry_after + jitter_amount

                            logger.warning(
                                f"Slack rate limit hit (429). Retrying in {sleep_time:.2f}s. "
                                f"Error: {e.response.get('error', 'Unknown')}"
                            )

                            # Wait before retrying
                            await asyncio.sleep(sleep_time)

                            # Increase delay for next potential retry using exponential backoff
                            delay *= backoff_factor
                        else:
                            # We've used all our retries
                            logger.error(f"Max retries ({max_retries}) reached for {func.__name__}")
                            raise
                    else:
                        # Not a rate limit error, don't retry
                        raise
                except Exception as e:
                    # For non-Slack API errors, don't retry
                    last_exception = e
                    raise

            # If we get here, we've exhausted all retries
            assert last_exception is not None
            raise last_exception

        return wrapper_async

    return decorator


def retry_slack_api_call(coro: Callable[..., Awaitable[R]]) -> Callable[..., Awaitable[R]]:
    """Simple decorator for retrying Slack API calls with default settings."""
    return with_slack_retry()(coro)
