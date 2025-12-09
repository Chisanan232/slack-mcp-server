"""Base OO-style Slack event handler.

This module provides an inheritance-based API for handling Slack Events API
payloads. Subclass :class:`BaseSlackEventHandler` and override one or more
``on_*`` methods to implement your logic.

Highlights
==========
- Automatic dispatch based on ``event['type']`` and optional ``event['subtype']``
- Naming convention: ``on_<type>()`` or ``on_<type>__<subtype>()`` (double underscore)
- Graceful fallback to :py:meth:`BaseSlackEventHandler.on_unknown`
- Works with :class:`slack_mcp.webhook.event.consumer.SlackEventConsumer`

Quick Example
=============
.. code-block:: python

    from slack_mcp.webhook.event.handler.base import BaseSlackEventHandler

    class MyHandler(BaseSlackEventHandler):
        async def on_app_mention(self, event):
            print("Mention:", event)

        async def on_message__channels(self, event):
            print("Channel message:", event)

Guidelines
==========
- Override only the events you need; others are no-ops by default.
- Use double underscore between type and subtype: ``on_message__im``.
- For unmatched events, :py:meth:`on_unknown` is called.

Payload Shape Notes
===================
The incoming ``event`` is the Slack Events API event body (dict). Common shapes:

- message
  .. code-block:: json

    {
      "type": "message",
      "channel": "C123",
      "user": "U123",
      "text": "hello",
      "ts": "1712345678.000100",
      "subtype": "channels"
    }

- reaction_added
  .. code-block:: json

    {
      "type": "reaction_added",
      "user": "U123",
      "reaction": "thumbsup",
      "item": {"type": "message", "channel": "C123", "ts": "1712345678.000100"},
      "event_ts": "1712345680.000200"
    }

References
==========
- Slack Events API: https://api.slack.com/apis/connections/events-api
- Event Types: https://api.slack.com/events
"""

from __future__ import annotations

import logging
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Protocol,
    cast,
    runtime_checkable,
)

__all__ = ["BaseSlackEventHandler", "EventHandler"]

_LOG = logging.getLogger(__name__)


@runtime_checkable
class EventHandler(Protocol):
    """Protocol for objects that can handle Slack events.

    Example
    -------
    .. code-block:: python

        class MyHandler:
            async def handle_event(self, event: Dict[str, Any]) -> None:
                print(event)
    """

    async def handle_event(self, event: Dict[str, Any]) -> None:
        """Handle a Slack event.

        Parameters
        ----------
        event : Dict[str, Any]
            The Slack event payload
        """
        ...


class BaseSlackEventHandler(EventHandler):
    """OO-style base class with automatic method dispatch for Slack events.

    Dispatch Rules
    --------------
    - First, try ``on_<type>__<subtype>()`` if ``event['subtype']`` is present
    - Else, try ``on_<type>()``
    - Else, call :py:meth:`on_unknown`

    Notes
    -----
    - Only implement methods you need; missing methods are treated as no-ops.
    - Use double underscore between type and subtype names.

    Best Practices
    --------------
    - Add structured logging including ``type``/``subtype`` and identifiers (e.g., ``channel``, ``user``, ``ts``).
    - Handle errors gracefully; never let exceptions crash the consumer loop.
    - Make handlers idempotent when possible (e.g., check for existing side effects).

    Examples
    --------
    .. code-block:: python

        class MyHandler(BaseSlackEventHandler):
            async def on_message(self, event):
                ...

            async def on_message__channels(self, event):
                ...
    
    Testing
    -------
    .. code-block:: python

        import asyncio

        h = MyHandler()
        asyncio.run(h.handle_event({
            "type": "message",
            "channel": "C123",
            "user": "U123",
            "text": "hello",
            "ts": "1712345678.000100"
        }))
    """

    # Main event entry point - called by the consumer
    async def handle_event(self, event: Dict[str, Any]) -> None:
        """Main entry point for handling Slack events.

        This method is called by the consumer and resolves to the appropriate
        ``on_*`` method following the dispatch rules. Do not override this;
        override the specific ``on_*`` handlers instead.

        Parameters
        ----------
        event : Dict[str, Any]
            The Slack event payload
        """
        fn = self._resolve(event)
        await fn(event)

    # ===== App Events =====

    async def on_app_deleted(self, event: Dict[str, Any]) -> None:
        """Handle app_deleted events."""

    async def on_app_home_opened(self, event: Dict[str, Any]) -> None:
        """Handle app_home_opened events."""

    async def on_app_installed(self, event: Dict[str, Any]) -> None:
        """Handle app_installed events."""

    async def on_app_mention(self, event: Dict[str, Any]) -> None:
        """Handle app_mention events.

        Notes
        -----
        - Typical fields: ``user``, ``channel``, ``text``, ``ts``.
        - Triggered when the app is mentioned in a channel or thread.

        References
        ----------
        - https://api.slack.com/events/app_mention
        """

    async def on_app_rate_limited(self, event: Dict[str, Any]) -> None:
        """Handle app_rate_limited events."""

    async def on_app_requested(self, event: Dict[str, Any]) -> None:
        """Handle app_requested events."""

    async def on_app_uninstalled(self, event: Dict[str, Any]) -> None:
        """Handle app_uninstalled events."""

    async def on_app_uninstalled_team(self, event: Dict[str, Any]) -> None:
        """Handle app_uninstalled_team events."""

    # ===== Assistant Events =====

    async def on_assistant_thread_context_changed(self, event: Dict[str, Any]) -> None:
        """Handle assistant_thread_context_changed events."""

    async def on_assistant_thread_started(self, event: Dict[str, Any]) -> None:
        """Handle assistant_thread_started events."""

    # ===== Call Events =====

    async def on_call_rejected(self, event: Dict[str, Any]) -> None:
        """Handle call_rejected events."""

    # ===== Channel Events =====

    async def on_channel_archive(self, event: Dict[str, Any]) -> None:
        """Handle channel_archive events."""

    async def on_channel_created(self, event: Dict[str, Any]) -> None:
        """Handle channel_created events."""

    async def on_channel_deleted(self, event: Dict[str, Any]) -> None:
        """Handle channel_deleted events."""

    async def on_channel_history_changed(self, event: Dict[str, Any]) -> None:
        """Handle channel_history_changed events."""

    async def on_channel_id_changed(self, event: Dict[str, Any]) -> None:
        """Handle channel_id_changed events."""

    async def on_channel_left(self, event: Dict[str, Any]) -> None:
        """Handle channel_left events."""

    async def on_channel_rename(self, event: Dict[str, Any]) -> None:
        """Handle channel_rename events."""

    async def on_channel_shared(self, event: Dict[str, Any]) -> None:
        """Handle channel_shared events."""

    async def on_channel_unarchive(self, event: Dict[str, Any]) -> None:
        """Handle channel_unarchive events."""

    async def on_channel_unshared(self, event: Dict[str, Any]) -> None:
        """Handle channel_unshared events."""

    # ===== DND (Do Not Disturb) Events =====

    async def on_dnd_updated(self, event: Dict[str, Any]) -> None:
        """Handle dnd_updated events."""

    async def on_dnd_updated_user(self, event: Dict[str, Any]) -> None:
        """Handle dnd_updated_user events."""

    # ===== Domain Events =====

    async def on_email_domain_changed(self, event: Dict[str, Any]) -> None:
        """Handle email_domain_changed events."""

    # ===== Emoji Events =====

    async def on_emoji_changed(self, event: Dict[str, Any]) -> None:
        """Handle emoji_changed events."""

    # ===== File Events =====

    async def on_file_change(self, event: Dict[str, Any]) -> None:
        """Handle file_change events."""

    async def on_file_comment_added(self, event: Dict[str, Any]) -> None:
        """Handle file_comment_added events."""

    async def on_file_comment_deleted(self, event: Dict[str, Any]) -> None:
        """Handle file_comment_deleted events."""

    async def on_file_comment_edited(self, event: Dict[str, Any]) -> None:
        """Handle file_comment_edited events."""

    async def on_file_created(self, event: Dict[str, Any]) -> None:
        """Handle file_created events."""

    async def on_file_deleted(self, event: Dict[str, Any]) -> None:
        """Handle file_deleted events."""

    async def on_file_public(self, event: Dict[str, Any]) -> None:
        """Handle file_public events."""

    async def on_file_shared(self, event: Dict[str, Any]) -> None:
        """Handle file_shared events."""

    async def on_file_unshared(self, event: Dict[str, Any]) -> None:
        """Handle file_unshared events."""

    # ===== Function Events =====

    async def on_function_executed(self, event: Dict[str, Any]) -> None:
        """Handle function_executed events."""

    # ===== Grid Migration Events =====

    async def on_grid_migration_finished(self, event: Dict[str, Any]) -> None:
        """Handle grid_migration_finished events."""

    async def on_grid_migration_started(self, event: Dict[str, Any]) -> None:
        """Handle grid_migration_started events."""

    # ===== Group Events =====

    async def on_group_archive(self, event: Dict[str, Any]) -> None:
        """Handle group_archive events."""

    async def on_group_close(self, event: Dict[str, Any]) -> None:
        """Handle group_close events."""

    async def on_group_deleted(self, event: Dict[str, Any]) -> None:
        """Handle group_deleted events."""

    async def on_group_history_changed(self, event: Dict[str, Any]) -> None:
        """Handle group_history_changed events."""

    async def on_group_left(self, event: Dict[str, Any]) -> None:
        """Handle group_left events."""

    async def on_group_open(self, event: Dict[str, Any]) -> None:
        """Handle group_open events."""

    async def on_group_rename(self, event: Dict[str, Any]) -> None:
        """Handle group_rename events."""

    async def on_group_unarchive(self, event: Dict[str, Any]) -> None:
        """Handle group_unarchive events."""

    # ===== IM (Direct Message) Events =====

    async def on_im_close(self, event: Dict[str, Any]) -> None:
        """Handle im_close events."""

    async def on_im_created(self, event: Dict[str, Any]) -> None:
        """Handle im_created events."""

    async def on_im_history_changed(self, event: Dict[str, Any]) -> None:
        """Handle im_history_changed events."""

    async def on_im_open(self, event: Dict[str, Any]) -> None:
        """Handle im_open events."""

    # ===== Invite Events =====

    async def on_invite_requested(self, event: Dict[str, Any]) -> None:
        """Handle invite_requested events.

        References
        ----------
        - https://api.slack.com/events/invite_requested
        """

    # ===== Link Events =====

    async def on_link_shared(self, event: Dict[str, Any]) -> None:
        """Handle link_shared events.

        Notes
        -----
        - Contains a list of shared links in the message context.

        References
        ----------
        - https://api.slack.com/events/link_shared
        """

    # ===== Member Events =====

    async def on_member_joined_channel(self, event: Dict[str, Any]) -> None:
        """Handle member_joined_channel events.

        Notes
        -----
        - Includes ``user``, ``channel``, and membership context.

        References
        ----------
        - https://api.slack.com/events/member_joined_channel
        """

    async def on_member_left_channel(self, event: Dict[str, Any]) -> None:
        """Handle member_left_channel events.

        Notes
        -----
        - Includes ``user``, ``channel``, and context about the membership change.

        References
        ----------
        - https://api.slack.com/events/member_left_channel
        """

    # ===== Message Events =====

    async def on_message(self, event: Dict[str, Any]) -> None:
        """Handle message events.

        Notes
        -----
        - For subtypes, implement ``on_message__<subtype>()`` (e.g., ``on_message__im``).
        - Common fields: ``channel``, ``user``, ``text``, ``ts``, optional ``subtype``.

        References
        ----------
        - https://api.slack.com/events/message
        """

    async def on_message__app_home(self, event: Dict[str, Any]) -> None:
        """Handle message.app_home events."""

    async def on_message__channels(self, event: Dict[str, Any]) -> None:
        """Handle message.channels events.

        Notes
        -----
        - Subtype of ``message`` in public channels.
        - See also :py:meth:`on_message` for common fields.
        """

    async def on_message__groups(self, event: Dict[str, Any]) -> None:
        """Handle message.groups events.

        Notes
        -----
        - Subtype of ``message`` in private channels (groups).
        - See also :py:meth:`on_message` for common fields.
        """

    async def on_message__im(self, event: Dict[str, Any]) -> None:
        """Handle message.im events.

        Notes
        -----
        - Subtype of ``message`` in direct messages.
        - See also :py:meth:`on_message` for common fields.
        """

    async def on_message__mpim(self, event: Dict[str, Any]) -> None:
        """Handle message.mpim events.

        Notes
        -----
        - Subtype of ``message`` in multi-person direct messages.
        - See also :py:meth:`on_message` for common fields.
        """

    # ===== Message Metadata Events =====

    async def on_message_metadata_deleted(self, event: Dict[str, Any]) -> None:
        """Handle message_metadata_deleted events.

        References
        ----------
        - https://api.slack.com/events/message_metadata_deleted
        """

    async def on_message_metadata_posted(self, event: Dict[str, Any]) -> None:
        """Handle message_metadata_posted events.

        References
        ----------
        - https://api.slack.com/events/message_metadata_posted
        """

    async def on_message_metadata_updated(self, event: Dict[str, Any]) -> None:
        """Handle message_metadata_updated events.

        References
        ----------
        - https://api.slack.com/events/message_metadata_updated
        """

    # ===== Pin Events =====

    async def on_pin_added(self, event: Dict[str, Any]) -> None:
        """Handle pin_added events.

        References
        ----------
        - https://api.slack.com/events/pin_added
        """

    async def on_pin_removed(self, event: Dict[str, Any]) -> None:
        """Handle pin_removed events.

        References
        ----------
        - https://api.slack.com/events/pin_removed
        """

    # ===== Reaction Events =====

    async def on_reaction_added(self, event: Dict[str, Any]) -> None:
        """Handle reaction_added events.

        Notes
        -----
        - Includes ``reaction`` and ``item`` describing the reacted-to entity.

        References
        ----------
        - https://api.slack.com/events/reaction_added
        """

    async def on_reaction_removed(self, event: Dict[str, Any]) -> None:
        """Handle reaction_removed events.

        References
        ----------
        - https://api.slack.com/events/reaction_removed
        """

    # ===== Resource Events =====

    async def on_resources_added(self, event: Dict[str, Any]) -> None:
        """Handle resources_added events."""

    async def on_resources_removed(self, event: Dict[str, Any]) -> None:
        """Handle resources_removed events."""

    # ===== Scope Events =====

    async def on_scope_denied(self, event: Dict[str, Any]) -> None:
        """Handle scope_denied events.

        References
        ----------
        - https://api.slack.com/events/scope_denied
        """

    async def on_scope_granted(self, event: Dict[str, Any]) -> None:
        """Handle scope_granted events.

        References
        ----------
        - https://api.slack.com/events/scope_granted
        """

    # ===== Shared Channel Events =====

    async def on_shared_channel_invite_accepted(self, event: Dict[str, Any]) -> None:
        """Handle shared_channel_invite_accepted events."""

    async def on_shared_channel_invite_approved(self, event: Dict[str, Any]) -> None:
        """Handle shared_channel_invite_approved events."""

    async def on_shared_channel_invite_declined(self, event: Dict[str, Any]) -> None:
        """Handle shared_channel_invite_declined events."""

    async def on_shared_channel_invite_received(self, event: Dict[str, Any]) -> None:
        """Handle shared_channel_invite_received events."""

    async def on_shared_channel_invite_requested(self, event: Dict[str, Any]) -> None:
        """Handle shared_channel_invite_requested events."""

    # ===== Star Events =====

    async def on_star_added(self, event: Dict[str, Any]) -> None:
        """Handle star_added events."""

    async def on_star_removed(self, event: Dict[str, Any]) -> None:
        """Handle star_removed events."""

    # ===== Subteam (User Group) Events =====

    async def on_subteam_created(self, event: Dict[str, Any]) -> None:
        """Handle subteam_created events.

        References
        ----------
        - https://api.slack.com/events/subteam_created
        """

    async def on_subteam_members_changed(self, event: Dict[str, Any]) -> None:
        """Handle subteam_members_changed events.

        Notes
        -----
        - Includes the list of added/removed users for the user group.

        References
        ----------
        - https://api.slack.com/events/subteam_members_changed
        """

    async def on_subteam_self_added(self, event: Dict[str, Any]) -> None:
        """Handle subteam_self_added events."""

    async def on_subteam_self_removed(self, event: Dict[str, Any]) -> None:
        """Handle subteam_self_removed events."""

    async def on_subteam_updated(self, event: Dict[str, Any]) -> None:
        """Handle subteam_updated events.

        References
        ----------
        - https://api.slack.com/events/subteam_updated
        """

    # ===== Team Access Events =====

    async def on_team_access_granted(self, event: Dict[str, Any]) -> None:
        """Handle team_access_granted events."""

    async def on_team_access_revoked(self, event: Dict[str, Any]) -> None:
        """Handle team_access_revoked events."""

    # ===== Team Events =====

    async def on_team_domain_change(self, event: Dict[str, Any]) -> None:
        """Handle team_domain_change events.

        References
        ----------
        - https://api.slack.com/events/team_domain_change
        """

    async def on_team_join(self, event: Dict[str, Any]) -> None:
        """Handle team_join events.

        Notes
        -----
        - Sent when a new user joins the workspace; payload includes ``user`` details.

        References
        ----------
        - https://api.slack.com/events/team_join
        """

    async def on_team_rename(self, event: Dict[str, Any]) -> None:
        """Handle team_rename events."""

    # ===== Token Events =====

    async def on_tokens_revoked(self, event: Dict[str, Any]) -> None:
        """Handle tokens_revoked events.

        References
        ----------
        - https://api.slack.com/events/tokens_revoked
        """

    # ===== URL Events =====

    async def on_url_verification(self, event: Dict[str, Any]) -> None:
        """Handle url_verification events.

        Notes
        -----
        - Typically handled at the HTTP level to respond with the ``challenge``.
        - May be enqueued and processed here if the webhook layer forwards it.

        References
        ----------
        - https://api.slack.com/events/url_verification
        """

    # ===== User Events =====

    async def on_user_change(self, event: Dict[str, Any]) -> None:
        """Handle user_change events.

        Notes
        -----
        - Fired when a user's profile or status changes.

        References
        ----------
        - https://api.slack.com/events/user_change
        """

    async def on_user_huddle_changed(self, event: Dict[str, Any]) -> None:
        """Handle user_huddle_changed events."""

    async def on_user_resource_denied(self, event: Dict[str, Any]) -> None:
        """Handle user_resource_denied events."""

    async def on_user_resource_granted(self, event: Dict[str, Any]) -> None:
        """Handle user_resource_granted events."""

    async def on_user_resource_removed(self, event: Dict[str, Any]) -> None:
        """Handle user_resource_removed events."""

    # ===== Workflow Events =====

    async def on_workflow_deleted(self, event: Dict[str, Any]) -> None:
        """Handle workflow_deleted events."""

    async def on_workflow_published(self, event: Dict[str, Any]) -> None:
        """Handle workflow_published events."""

    async def on_workflow_step_deleted(self, event: Dict[str, Any]) -> None:
        """Handle workflow_step_deleted events."""

    async def on_workflow_step_execute(self, event: Dict[str, Any]) -> None:
        """Handle workflow_step_execute events."""

    async def on_workflow_unpublished(self, event: Dict[str, Any]) -> None:
        """Handle workflow_unpublished events."""

    # ===== Catch-all handler =====

    async def on_unknown(self, event: Dict[str, Any]) -> None:
        """Handle events with no matching handler.

        This is called as a fallback when no specific handler is found.
        Default implementation is a no-op.

        Parameters
        ----------
        event : Dict[str, Any]
            The Slack event payload
        """

    # Private method to resolve the appropriate handler

    def _resolve(self, event: Dict[str, Any]) -> Callable[[Dict[str, Any]], Awaitable[None]]:
        """Resolve the handler method for an event.

        Precedence
        ----------
        1. ``on_<type>__<subtype>`` when ``event['subtype']`` is present
        2. ``on_<type>``
        3. :py:meth:`on_unknown`

        Parameters
        ----------
        event : Dict[str, Any]
            The Slack event payload

        Returns
        -------
        Callable[[Dict[str, Any]], Awaitable[None]]
            The handler method to call for this event
        """
        event_type = event.get("type", "unknown")
        subtype = event.get("subtype")

        # First priority: type + subtype
        if subtype:
            name = f"on_{event_type}__{subtype}"
            fn = getattr(self, name, None)
            if fn:
                return cast(Callable[[Dict[str, Any]], Awaitable[None]], fn)

        # Second priority: just type
        name = f"on_{event_type}"
        fn = getattr(self, name, None)
        if fn:
            return cast(Callable[[Dict[str, Any]], Awaitable[None]], fn)

        # Last resort: unknown handler
        return self.on_unknown
