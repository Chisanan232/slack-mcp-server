"""
Global pytest configuration to handle event loop management.

This file ensures proper handling of asyncio event loops in tests,
particularly to prevent "Event loop is closed" errors in CI environments.
"""

import asyncio
import logging
import os
import sys
import threading
import tracemalloc
import warnings
from typing import Generator

import pytest


@pytest.fixture(scope="session", autouse=True)
def enable_tracemalloc():
    """Enable tracemalloc at the start of the test session for better debugging of warnings."""
    tracemalloc.start(5)  # Start with 5 frames to get detailed allocation info
    yield
    tracemalloc.stop()


# Enable tracemalloc for threads as well
threading.excepthook = lambda args: tracemalloc.get_object_traceback(args.exc_value)


@pytest.fixture(scope="session", autouse=True)
def set_event_loop_policy():
    """Configure the event loop policy for tests based on platform and environment."""
    # For CI environments on macOS, use a custom policy to avoid "Event loop is closed" errors
    from slack_mcp.settings import is_ci_environment
    if sys.platform == "darwin" and is_ci_environment():
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

    # For local environments, use the default policy
    yield

    # Clean up at the end of the session
    try:
        # Get the current event loop if one exists, using the new API to avoid deprecation warnings
        try:
            # Use get_running_loop() if there's a running loop, otherwise create a new one
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop, create a new one
                loop = asyncio.new_event_loop()

            if loop.is_running():
                loop.stop()
            if not loop.is_closed():
                loop.close()
        except RuntimeError:
            # No event loop exists - that's fine
            pass
    except Exception:
        # Log but don't fail the test session
        logging.exception("Error during event loop cleanup")


@pytest.fixture(scope="function")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create an isolated event loop for each test.

    This fixture overrides pytest-asyncio's default event_loop fixture to ensure
    proper setup and cleanup, particularly in CI environments.
    """
    # Create a new loop for the test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Increase timeouts for CI environments
    from slack_mcp.settings import is_ci_environment
    if is_ci_environment():
        # CI environments might be slower, so use longer timeouts
        loop.slow_callback_duration = 1.0
        # Set a higher timeout for shutting down the loop
        shutdown_timeout = 2.0
    else:
        # For local development, use shorter timeouts
        loop.slow_callback_duration = 0.25
        shutdown_timeout = 0.5

    yield loop

    # Clean up the loop after the test
    try:
        # Cancel all pending tasks
        pending_tasks = asyncio.all_tasks(loop)
        if pending_tasks:
            for task in pending_tasks:
                if not task.done() and not task.cancelled():
                    task.cancel()

            # Wait for tasks to be cancelled with a timeout
            try:
                # Use gather with return_exceptions to avoid task cancellation errors
                loop.run_until_complete(
                    asyncio.wait_for(asyncio.gather(*pending_tasks, return_exceptions=True), timeout=shutdown_timeout)
                )
            except (asyncio.CancelledError, asyncio.TimeoutError, RuntimeError):
                # Ignore cancellation, timeout, and "loop is closed" errors
                pass
    except RuntimeError as e:
        if "Event loop is closed" in str(e):
            # The loop is already closed, nothing more to do
            pass
        else:
            # Log other runtime errors but don't fail the test
            warnings.warn(f"Error during event loop cleanup: {e}")
    except Exception as e:
        # Log other exceptions but don't fail the test
        warnings.warn(f"Exception during event loop cleanup: {e}")

    # Close the loop if it's not already closed
    try:
        if not loop.is_closed():
            loop.close()
    except Exception:
        pass

    # Create a new event loop and make it the current one
    # This ensures that subsequent tests don't reuse a closed loop
    asyncio.set_event_loop(asyncio.new_event_loop())


@pytest.fixture(scope="function")
def anyio_backend():
    """
    Configure anyio backend to use asyncio.

    This ensures consistent behavior across all async tests.
    """
    return "asyncio"
