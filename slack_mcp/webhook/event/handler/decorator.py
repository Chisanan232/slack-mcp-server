"""
Decorator-based Slack event handler implementation.

This module provides a class-based decorator handler for Slack events that can be used
in two ways:
1. Attribute-style: @handler.reaction_added
2. Enum-style: @handler(SlackEvent.REACTION_ADDED)

This handler implements the EventHandler protocol and can be registered with a SlackEventConsumer.
"""

from __future__ import annotations

import inspect
import logging
from collections import defaultdict
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    cast,
    overload,
)

from slack_mcp.events import SlackEvent

from .base import EventHandler

__all__ = ["DecoratorHandler"]

_LOG = logging.getLogger("slack_mcp.handler.decorator")

# Type for event handlers - can be sync or async functions
# F = TypeVar("F", bound=Callable[[Dict[str, Any]], Any])
HandlerFunc = Callable[[Dict[str, Any]], Awaitable[Any] | Any]


class DecoratorHandler(EventHandler):
    """Decorator-based Slack event handler.

    This class implements the EventHandler protocol and provides decorator-style
    registration of event handlers. It can be used in two ways:

    1. Attribute-style:
       ```python
       handler = DecoratorHandler()

       @handler.reaction_added
       def handle_reaction(event):
           # Handle reaction_added event
       ```

    2. Enum-style:
       ```python
       handler = DecoratorHandler()

       @handler(SlackEvent.REACTION_ADDED)
       def handle_reaction(event):
           # Handle reaction_added event
       ```

    The handler can be registered with a SlackEventConsumer:
    ```python
    consumer = SlackEventConsumer(backend, handler=handler)
    ```

    This class provides explicit methods for all Slack event types for better
    IDE auto-completion.
    """

    def __init__(self) -> None:
        """Initialize the decorator handler with an empty registry."""
        self._handlers: Dict[str, List[HandlerFunc]] = defaultdict(list)

    @overload
    def __call__[F](self, ev: SlackEvent) -> Callable[[F], F]: ...

    @overload
    def __call__[F](self, ev: str) -> Callable[[F], F]: ...

    @overload
    def __call__[F](self, ev: F) -> F: ...

    def __call__[F](self, ev: SlackEvent | str | F) -> Callable[[HandlerFunc], HandlerFunc] | F:
        """Register a function as a handler for a specific event type.

        This method can be used in two ways:
        1. As a direct decorator: @handler
           In this case, registers for the wildcard event "*"
        2. With an argument: @handler(SlackEvent.X) or @handler("event.subtype")

        Parameters
        ----------
        ev : SlackEvent | str | F
            Either a SlackEvent enum, a string event type, or the function to decorate

        Returns
        -------
        Callable[[HandlerFunc], HandlerFunc] | F
            Either a decorator function or the decorated function
        """
        # Case 1: @handler (no args) - register for wildcard "*"
        if callable(ev) and not isinstance(ev, (str, SlackEvent)):
            fn = cast(F, ev)
            self._handlers["*"].append(fn)
            return fn

        # Case 2: @handler(SlackEvent.X) or @handler("event.subtype")
        event_name = str(ev)  # Works for both str and SlackEvent

        def decorator(_fn: HandlerFunc) -> HandlerFunc:
            self._handlers[event_name].append(_fn)
            return _fn

        return decorator

    def __getattr__[F](self, name: str) -> Callable[[F], F]:
        """Support attribute-style registration (@handler.reaction_added).

        Parameters
        ----------
        name : str
            The attribute name, representing an event type with underscores
            instead of dots

        Returns
        -------
        Callable
            A decorator function that will register the decorated function

        Raises
        ------
        AttributeError
            If the attribute doesn't correspond to a valid SlackEvent
        """
        try:
            # Try to convert attribute_name to a valid SlackEvent
            # First try direct match (e.g., "reaction_added" -> SlackEvent.REACTION_ADDED)
            try:
                event_enum = getattr(SlackEvent, name.upper())
                return self(event_enum)
            except (AttributeError, ValueError):
                # If that fails, try with dots instead of underscores
                event_name = name.replace("_", ".")
                # Validate against Enum if possible
                try:
                    ev = SlackEvent(event_name)
                    return self(ev)
                except ValueError:
                    # If not a standard event, allow custom event types
                    return self(name)
        except Exception:
            raise AttributeError(f"Unknown Slack event type: '{name}'")

    async def handle_event(self, event: Dict[str, Any]) -> None:
        """Handle a Slack event by routing it to registered handlers.

        This method implements the EventHandler protocol and is called by
        the SlackEventConsumer.

        Parameters
        ----------
        event : Dict[str, Any]
            The Slack event payload
        """
        event_type = event.get("type", "unknown")
        event_subtype = event.get("subtype")

        # Collect all applicable handlers
        handlers_to_call = []

        # Add wildcard handlers
        handlers_to_call.extend(self._handlers.get("*", []))

        # Add handlers for this specific event type
        handlers_to_call.extend(self._handlers.get(event_type, []))

        # Add handlers for event type + subtype (if present)
        if event_subtype:
            combined_type = f"{event_type}.{event_subtype}"
            handlers_to_call.extend(self._handlers.get(combined_type, []))

        # Call all handlers
        for handler in handlers_to_call:
            try:
                result = handler(event)
                # If it's a coroutine, await it
                if inspect.isawaitable(result):
                    await result
            except Exception as e:
                _LOG.exception(f"Error in event handler for {event_type}: {e}")

    def get_handlers(self) -> Dict[str, List[HandlerFunc]]:
        """Get a copy of all registered handlers.

        Returns
        -------
        Dict[str, List[HandlerFunc]]
            A dictionary mapping event types to lists of handler functions
        """
        return dict(self._handlers)

    def clear_handlers(self) -> None:
        """Clear all registered event handlers.

        This is primarily useful for testing or for reloading handlers at runtime.
        """
        self._handlers.clear()

    # Explicit methods for all Slack event types for better IDE auto-completion

    # Standard events
    def app_deleted[F](self, fn: F) -> F:
        """Register a handler for app_deleted events."""
        return self(SlackEvent.APP_DELETED)(fn)

    def app_home_opened[F](self, fn: F) -> F:
        """Register a handler for app_home_opened events."""
        return self(SlackEvent.APP_HOME_OPENED)(fn)

    def app_installed[F](self, fn: F) -> F:
        """Register a handler for app_installed events."""
        return self(SlackEvent.APP_INSTALLED)(fn)

    def app_mention[F](self, fn: F) -> F:
        """Register a handler for app_mention events."""
        return self(SlackEvent.APP_MENTION)(fn)

    def app_rate_limited[F](self, fn: F) -> F:
        """Register a handler for app_rate_limited events."""
        return self(SlackEvent.APP_RATE_LIMITED)(fn)

    def app_requested[F](self, fn: F) -> F:
        """Register a handler for app_requested events."""
        return self(SlackEvent.APP_REQUESTED)(fn)

    def app_uninstalled[F](self, fn: F) -> F:
        """Register a handler for app_uninstalled events."""
        return self(SlackEvent.APP_UNINSTALLED)(fn)

    def app_uninstalled_team[F](self, fn: F) -> F:
        """Register a handler for app_uninstalled_team events."""
        return self(SlackEvent.APP_UNINSTALLED_TEAM)(fn)

    def assistant_thread_context_changed[F](self, fn: F) -> F:
        """Register a handler for assistant_thread_context_changed events."""
        return self(SlackEvent.ASSISTANT_THREAD_CONTEXT_CHANGED)(fn)

    def assistant_thread_started[F](self, fn: F) -> F:
        """Register a handler for assistant_thread_started events."""
        return self(SlackEvent.ASSISTANT_THREAD_STARTED)(fn)

    def call_rejected[F](self, fn: F) -> F:
        """Register a handler for call_rejected events."""
        return self(SlackEvent.CALL_REJECTED)(fn)

    def channel_archive[F](self, fn: F) -> F:
        """Register a handler for channel_archive events."""
        return self(SlackEvent.CHANNEL_ARCHIVE)(fn)

    def channel_created[F](self, fn: F) -> F:
        """Register a handler for channel_created events."""
        return self(SlackEvent.CHANNEL_CREATED)(fn)

    def channel_deleted[F](self, fn: F) -> F:
        """Register a handler for channel_deleted events."""
        return self(SlackEvent.CHANNEL_DELETED)(fn)

    def channel_history_changed[F](self, fn: F) -> F:
        """Register a handler for channel_history_changed events."""
        return self(SlackEvent.CHANNEL_HISTORY_CHANGED)(fn)

    def channel_id_changed[F](self, fn: F) -> F:
        """Register a handler for channel_id_changed events."""
        return self(SlackEvent.CHANNEL_ID_CHANGED)(fn)

    def channel_left[F](self, fn: F) -> F:
        """Register a handler for channel_left events."""
        return self(SlackEvent.CHANNEL_LEFT)(fn)

    def channel_rename[F](self, fn: F) -> F:
        """Register a handler for channel_rename events."""
        return self(SlackEvent.CHANNEL_RENAME)(fn)

    def channel_shared[F](self, fn: F) -> F:
        """Register a handler for channel_shared events."""
        return self(SlackEvent.CHANNEL_SHARED)(fn)

    def channel_unarchive[F](self, fn: F) -> F:
        """Register a handler for channel_unarchive events."""
        return self(SlackEvent.CHANNEL_UNARCHIVE)(fn)

    def channel_unshared[F](self, fn: F) -> F:
        """Register a handler for channel_unshared events."""
        return self(SlackEvent.CHANNEL_UNSHARED)(fn)

    def dnd_updated[F](self, fn: F) -> F:
        """Register a handler for dnd_updated events."""
        return self(SlackEvent.DND_UPDATED)(fn)

    def dnd_updated_user[F](self, fn: F) -> F:
        """Register a handler for dnd_updated_user events."""
        return self(SlackEvent.DND_UPDATED_USER)(fn)

    def email_domain_changed[F](self, fn: F) -> F:
        """Register a handler for email_domain_changed events."""
        return self(SlackEvent.EMAIL_DOMAIN_CHANGED)(fn)

    def emoji_changed[F](self, fn: F) -> F:
        """Register a handler for emoji_changed events."""
        return self(SlackEvent.EMOJI_CHANGED)(fn)

    def file_change[F](self, fn: F) -> F:
        """Register a handler for file_change events."""
        return self(SlackEvent.FILE_CHANGE)(fn)

    def file_comment_added[F](self, fn: F) -> F:
        """Register a handler for file_comment_added events."""
        return self(SlackEvent.FILE_COMMENT_ADDED)(fn)

    def file_comment_deleted[F](self, fn: F) -> F:
        """Register a handler for file_comment_deleted events."""
        return self(SlackEvent.FILE_COMMENT_DELETED)(fn)

    def file_comment_edited[F](self, fn: F) -> F:
        """Register a handler for file_comment_edited events."""
        return self(SlackEvent.FILE_COMMENT_EDITED)(fn)

    def file_created[F](self, fn: F) -> F:
        """Register a handler for file_created events."""
        return self(SlackEvent.FILE_CREATED)(fn)

    def file_deleted[F](self, fn: F) -> F:
        """Register a handler for file_deleted events."""
        return self(SlackEvent.FILE_DELETED)(fn)

    def file_public[F](self, fn: F) -> F:
        """Register a handler for file_public events."""
        return self(SlackEvent.FILE_PUBLIC)(fn)

    def file_shared[F](self, fn: F) -> F:
        """Register a handler for file_shared events."""
        return self(SlackEvent.FILE_SHARED)(fn)

    def file_unshared[F](self, fn: F) -> F:
        """Register a handler for file_unshared events."""
        return self(SlackEvent.FILE_UNSHARED)(fn)

    def function_executed[F](self, fn: F) -> F:
        """Register a handler for function_executed events."""
        return self(SlackEvent.FUNCTION_EXECUTED)(fn)

    def grid_migration_finished[F](self, fn: F) -> F:
        """Register a handler for grid_migration_finished events."""
        return self(SlackEvent.GRID_MIGRATION_FINISHED)(fn)

    def grid_migration_started[F](self, fn: F) -> F:
        """Register a handler for grid_migration_started events."""
        return self(SlackEvent.GRID_MIGRATION_STARTED)(fn)

    def group_archive[F](self, fn: F) -> F:
        """Register a handler for group_archive events."""
        return self(SlackEvent.GROUP_ARCHIVE)(fn)

    def group_close[F](self, fn: F) -> F:
        """Register a handler for group_close events."""
        return self(SlackEvent.GROUP_CLOSE)(fn)

    def group_deleted[F](self, fn: F) -> F:
        """Register a handler for group_deleted events."""
        return self(SlackEvent.GROUP_DELETED)(fn)

    def group_history_changed[F](self, fn: F) -> F:
        """Register a handler for group_history_changed events."""
        return self(SlackEvent.GROUP_HISTORY_CHANGED)(fn)

    def group_left[F](self, fn: F) -> F:
        """Register a handler for group_left events."""
        return self(SlackEvent.GROUP_LEFT)(fn)

    def group_open[F](self, fn: F) -> F:
        """Register a handler for group_open events."""
        return self(SlackEvent.GROUP_OPEN)(fn)

    def group_rename[F](self, fn: F) -> F:
        """Register a handler for group_rename events."""
        return self(SlackEvent.GROUP_RENAME)(fn)

    def group_unarchive[F](self, fn: F) -> F:
        """Register a handler for group_unarchive events."""
        return self(SlackEvent.GROUP_UNARCHIVE)(fn)

    def im_close[F](self, fn: F) -> F:
        """Register a handler for im_close events."""
        return self(SlackEvent.IM_CLOSE)(fn)

    def im_created[F](self, fn: F) -> F:
        """Register a handler for im_created events."""
        return self(SlackEvent.IM_CREATED)(fn)

    def im_history_changed[F](self, fn: F) -> F:
        """Register a handler for im_history_changed events."""
        return self(SlackEvent.IM_HISTORY_CHANGED)(fn)

    def im_open[F](self, fn: F) -> F:
        """Register a handler for im_open events."""
        return self(SlackEvent.IM_OPEN)(fn)

    def invite_requested[F](self, fn: F) -> F:
        """Register a handler for invite_requested events."""
        return self(SlackEvent.INVITE_REQUESTED)(fn)

    def link_shared[F](self, fn: F) -> F:
        """Register a handler for link_shared events."""
        return self(SlackEvent.LINK_SHARED)(fn)

    def member_joined_channel[F](self, fn: F) -> F:
        """Register a handler for member_joined_channel events."""
        return self(SlackEvent.MEMBER_JOINED_CHANNEL)(fn)

    def member_left_channel[F](self, fn: F) -> F:
        """Register a handler for member_left_channel events."""
        return self(SlackEvent.MEMBER_LEFT_CHANNEL)(fn)

    def message[F](self, fn: F) -> F:
        """Register a handler for message events."""
        return self(SlackEvent.MESSAGE)(fn)

    def message_metadata_deleted[F](self, fn: F) -> F:
        """Register a handler for message_metadata_deleted events."""
        return self(SlackEvent.MESSAGE_METADATA_DELETED)(fn)

    def message_metadata_posted[F](self, fn: F) -> F:
        """Register a handler for message_metadata_posted events."""
        return self(SlackEvent.MESSAGE_METADATA_POSTED)(fn)

    def message_metadata_updated[F](self, fn: F) -> F:
        """Register a handler for message_metadata_updated events."""
        return self(SlackEvent.MESSAGE_METADATA_UPDATED)(fn)

    def pin_added[F](self, fn: F) -> F:
        """Register a handler for pin_added events."""
        return self(SlackEvent.PIN_ADDED)(fn)

    def pin_removed[F](self, fn: F) -> F:
        """Register a handler for pin_removed events."""
        return self(SlackEvent.PIN_REMOVED)(fn)

    def reaction_added[F](self, fn: F) -> F:
        """Register a handler for reaction_added events."""
        return self(SlackEvent.REACTION_ADDED)(fn)

    def reaction_removed[F](self, fn: F) -> F:
        """Register a handler for reaction_removed events."""
        return self(SlackEvent.REACTION_REMOVED)(fn)

    def resources_added[F](self, fn: F) -> F:
        """Register a handler for resources_added events."""
        return self(SlackEvent.RESOURCES_ADDED)(fn)

    def resources_removed[F](self, fn: F) -> F:
        """Register a handler for resources_removed events."""
        return self(SlackEvent.RESOURCES_REMOVED)(fn)

    def scope_denied[F](self, fn: F) -> F:
        """Register a handler for scope_denied events."""
        return self(SlackEvent.SCOPE_DENIED)(fn)

    def scope_granted[F](self, fn: F) -> F:
        """Register a handler for scope_granted events."""
        return self(SlackEvent.SCOPE_GRANTED)(fn)

    def star_added[F](self, fn: F) -> F:
        """Register a handler for star_added events."""
        return self(SlackEvent.STAR_ADDED)(fn)

    def star_removed[F](self, fn: F) -> F:
        """Register a handler for star_removed events."""
        return self(SlackEvent.STAR_REMOVED)(fn)

    def subteam_created[F](self, fn: F) -> F:
        """Register a handler for subteam_created events."""
        return self(SlackEvent.SUBTEAM_CREATED)(fn)

    def subteam_members_changed[F](self, fn: F) -> F:
        """Register a handler for subteam_members_changed events."""
        return self(SlackEvent.SUBTEAM_MEMBERS_CHANGED)(fn)

    def subteam_self_added[F](self, fn: F) -> F:
        """Register a handler for subteam_self_added events."""
        return self(SlackEvent.SUBTEAM_SELF_ADDED)(fn)

    def subteam_self_removed[F](self, fn: F) -> F:
        """Register a handler for subteam_self_removed events."""
        return self(SlackEvent.SUBTEAM_SELF_REMOVED)(fn)

    def subteam_updated[F](self, fn: F) -> F:
        """Register a handler for subteam_updated events."""
        return self(SlackEvent.SUBTEAM_UPDATED)(fn)

    def team_domain_change[F](self, fn: F) -> F:
        """Register a handler for team_domain_change events."""
        return self(SlackEvent.TEAM_DOMAIN_CHANGE)(fn)

    def team_join[F](self, fn: F) -> F:
        """Register a handler for team_join events."""
        return self(SlackEvent.TEAM_JOIN)(fn)

    def team_rename[F](self, fn: F) -> F:
        """Register a handler for team_rename events."""
        return self(SlackEvent.TEAM_RENAME)(fn)

    def tokens_revoked[F](self, fn: F) -> F:
        """Register a handler for tokens_revoked events."""
        return self(SlackEvent.TOKENS_REVOKED)(fn)

    def url_verification[F](self, fn: F) -> F:
        """Register a handler for url_verification events."""
        return self(SlackEvent.URL_VERIFICATION)(fn)

    def user_change[F](self, fn: F) -> F:
        """Register a handler for user_change events."""
        return self(SlackEvent.USER_CHANGE)(fn)

    def workflow_deleted[F](self, fn: F) -> F:
        """Register a handler for workflow_deleted events."""
        return self(SlackEvent.WORKFLOW_DELETED)(fn)

    def workflow_published[F](self, fn: F) -> F:
        """Register a handler for workflow_published events."""
        return self(SlackEvent.WORKFLOW_PUBLISHED)(fn)

    def workflow_unpublished[F](self, fn: F) -> F:
        """Register a handler for workflow_unpublished events."""
        return self(SlackEvent.WORKFLOW_UNPUBLISHED)(fn)

    # Message subtypes
    def message_channels[F](self, fn: F) -> F:
        """Register a handler for message.channels events."""
        return self(SlackEvent.MESSAGE_CHANNELS)(fn)

    def message_groups[F](self, fn: F) -> F:
        """Register a handler for message.groups events."""
        return self(SlackEvent.MESSAGE_GROUPS)(fn)

    def message_im[F](self, fn: F) -> F:
        """Register a handler for message.im events."""
        return self(SlackEvent.MESSAGE_IM)(fn)

    def message_mpim[F](self, fn: F) -> F:
        """Register a handler for message.mpim events."""
        return self(SlackEvent.MESSAGE_MPIM)(fn)
