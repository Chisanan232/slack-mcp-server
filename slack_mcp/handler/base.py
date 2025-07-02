"""
Base event handler for Slack events using OO-style inheritance pattern.

This module provides a base class for handling Slack events, where developers
can subclass and override methods for specific event types they care about.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Callable, Awaitable, Optional, cast

__all__ = ["BaseSlackEventHandler"]

_LOG = logging.getLogger("slack_mcp.handler.base")


class BaseSlackEventHandler:
    """Base class for handling Slack events using OO-style inheritance.
    
    This class automatically routes Slack events to appropriate methods based on their
    type and subtype using the pattern:
        event["type"] -> on_<type>()
        event["type"] + event["subtype"] -> on_<type>__<subtype>()  (double underscore)
    
    Any unimplemented methods will be no-ops.
    """

    # Main event entry point - called by the consumer
    async def handle_event(self, event: Dict[str, Any]) -> None:
        """Main entry point for handling Slack events.
        
        This method is called by the SlackEventConsumer and should not be 
        overridden by subclasses. Instead, override the specific on_* methods.
        
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
        pass
        
    async def on_app_home_opened(self, event: Dict[str, Any]) -> None:
        """Handle app_home_opened events."""
        pass
        
    async def on_app_installed(self, event: Dict[str, Any]) -> None:
        """Handle app_installed events."""
        pass
        
    async def on_app_mention(self, event: Dict[str, Any]) -> None:
        """Handle app_mention events."""
        pass
    
    async def on_app_rate_limited(self, event: Dict[str, Any]) -> None:
        """Handle app_rate_limited events."""
        pass
    
    async def on_app_requested(self, event: Dict[str, Any]) -> None:
        """Handle app_requested events."""
        pass
    
    async def on_app_uninstalled(self, event: Dict[str, Any]) -> None:
        """Handle app_uninstalled events."""
        pass
    
    async def on_app_uninstalled_team(self, event: Dict[str, Any]) -> None:
        """Handle app_uninstalled_team events."""
        pass
    
    # ===== Assistant Events =====
    
    async def on_assistant_thread_context_changed(self, event: Dict[str, Any]) -> None:
        """Handle assistant_thread_context_changed events."""
        pass
    
    async def on_assistant_thread_started(self, event: Dict[str, Any]) -> None:
        """Handle assistant_thread_started events."""
        pass
    
    # ===== Call Events =====
    
    async def on_call_rejected(self, event: Dict[str, Any]) -> None:
        """Handle call_rejected events."""
        pass
    
    # ===== Channel Events =====
    
    async def on_channel_archive(self, event: Dict[str, Any]) -> None:
        """Handle channel_archive events."""
        pass
    
    async def on_channel_created(self, event: Dict[str, Any]) -> None:
        """Handle channel_created events."""
        pass
    
    async def on_channel_deleted(self, event: Dict[str, Any]) -> None:
        """Handle channel_deleted events."""
        pass
    
    async def on_channel_history_changed(self, event: Dict[str, Any]) -> None:
        """Handle channel_history_changed events."""
        pass
    
    async def on_channel_id_changed(self, event: Dict[str, Any]) -> None:
        """Handle channel_id_changed events."""
        pass
    
    async def on_channel_left(self, event: Dict[str, Any]) -> None:
        """Handle channel_left events."""
        pass
    
    async def on_channel_rename(self, event: Dict[str, Any]) -> None:
        """Handle channel_rename events."""
        pass
    
    async def on_channel_shared(self, event: Dict[str, Any]) -> None:
        """Handle channel_shared events."""
        pass
    
    async def on_channel_unarchive(self, event: Dict[str, Any]) -> None:
        """Handle channel_unarchive events."""
        pass
    
    async def on_channel_unshared(self, event: Dict[str, Any]) -> None:
        """Handle channel_unshared events."""
        pass
    
    # ===== DND (Do Not Disturb) Events =====
    
    async def on_dnd_updated(self, event: Dict[str, Any]) -> None:
        """Handle dnd_updated events."""
        pass
    
    async def on_dnd_updated_user(self, event: Dict[str, Any]) -> None:
        """Handle dnd_updated_user events."""
        pass
    
    # ===== Domain Events =====
    
    async def on_email_domain_changed(self, event: Dict[str, Any]) -> None:
        """Handle email_domain_changed events."""
        pass
    
    # ===== Emoji Events =====
    
    async def on_emoji_changed(self, event: Dict[str, Any]) -> None:
        """Handle emoji_changed events."""
        pass
    
    # ===== File Events =====
    
    async def on_file_change(self, event: Dict[str, Any]) -> None:
        """Handle file_change events."""
        pass
    
    async def on_file_comment_added(self, event: Dict[str, Any]) -> None:
        """Handle file_comment_added events."""
        pass
    
    async def on_file_comment_deleted(self, event: Dict[str, Any]) -> None:
        """Handle file_comment_deleted events."""
        pass
    
    async def on_file_comment_edited(self, event: Dict[str, Any]) -> None:
        """Handle file_comment_edited events."""
        pass
    
    async def on_file_created(self, event: Dict[str, Any]) -> None:
        """Handle file_created events."""
        pass
    
    async def on_file_deleted(self, event: Dict[str, Any]) -> None:
        """Handle file_deleted events."""
        pass
    
    async def on_file_public(self, event: Dict[str, Any]) -> None:
        """Handle file_public events."""
        pass
    
    async def on_file_shared(self, event: Dict[str, Any]) -> None:
        """Handle file_shared events."""
        pass
    
    async def on_file_unshared(self, event: Dict[str, Any]) -> None:
        """Handle file_unshared events."""
        pass
    
    # ===== Function Events =====
    
    async def on_function_executed(self, event: Dict[str, Any]) -> None:
        """Handle function_executed events."""
        pass
    
    # ===== Grid Migration Events =====
    
    async def on_grid_migration_finished(self, event: Dict[str, Any]) -> None:
        """Handle grid_migration_finished events."""
        pass
    
    async def on_grid_migration_started(self, event: Dict[str, Any]) -> None:
        """Handle grid_migration_started events."""
        pass
    
    # ===== Group Events =====
    
    async def on_group_archive(self, event: Dict[str, Any]) -> None:
        """Handle group_archive events."""
        pass
    
    async def on_group_close(self, event: Dict[str, Any]) -> None:
        """Handle group_close events."""
        pass
    
    async def on_group_deleted(self, event: Dict[str, Any]) -> None:
        """Handle group_deleted events."""
        pass
    
    async def on_group_history_changed(self, event: Dict[str, Any]) -> None:
        """Handle group_history_changed events."""
        pass
    
    async def on_group_left(self, event: Dict[str, Any]) -> None:
        """Handle group_left events."""
        pass
    
    async def on_group_open(self, event: Dict[str, Any]) -> None:
        """Handle group_open events."""
        pass
    
    async def on_group_rename(self, event: Dict[str, Any]) -> None:
        """Handle group_rename events."""
        pass
    
    async def on_group_unarchive(self, event: Dict[str, Any]) -> None:
        """Handle group_unarchive events."""
        pass
    
    # ===== IM (Direct Message) Events =====
    
    async def on_im_close(self, event: Dict[str, Any]) -> None:
        """Handle im_close events."""
        pass
    
    async def on_im_created(self, event: Dict[str, Any]) -> None:
        """Handle im_created events."""
        pass
    
    async def on_im_history_changed(self, event: Dict[str, Any]) -> None:
        """Handle im_history_changed events."""
        pass
    
    async def on_im_open(self, event: Dict[str, Any]) -> None:
        """Handle im_open events."""
        pass
    
    # ===== Invite Events =====
    
    async def on_invite_requested(self, event: Dict[str, Any]) -> None:
        """Handle invite_requested events."""
        pass
    
    # ===== Link Events =====
    
    async def on_link_shared(self, event: Dict[str, Any]) -> None:
        """Handle link_shared events."""
        pass
    
    # ===== Member Events =====
    
    async def on_member_joined_channel(self, event: Dict[str, Any]) -> None:
        """Handle member_joined_channel events."""
        pass
    
    async def on_member_left_channel(self, event: Dict[str, Any]) -> None:
        """Handle member_left_channel events."""
        pass
    
    # ===== Message Events =====
    
    async def on_message(self, event: Dict[str, Any]) -> None:
        """Handle message events."""
        pass
    
    async def on_message__app_home(self, event: Dict[str, Any]) -> None:
        """Handle message.app_home events."""
        pass
    
    async def on_message__channels(self, event: Dict[str, Any]) -> None:
        """Handle message.channels events."""
        pass
    
    async def on_message__groups(self, event: Dict[str, Any]) -> None:
        """Handle message.groups events."""
        pass
    
    async def on_message__im(self, event: Dict[str, Any]) -> None:
        """Handle message.im events."""
        pass
    
    async def on_message__mpim(self, event: Dict[str, Any]) -> None:
        """Handle message.mpim events."""
        pass
    
    # ===== Message Metadata Events =====
    
    async def on_message_metadata_deleted(self, event: Dict[str, Any]) -> None:
        """Handle message_metadata_deleted events."""
        pass
    
    async def on_message_metadata_posted(self, event: Dict[str, Any]) -> None:
        """Handle message_metadata_posted events."""
        pass
    
    async def on_message_metadata_updated(self, event: Dict[str, Any]) -> None:
        """Handle message_metadata_updated events."""
        pass
    
    # ===== Pin Events =====
    
    async def on_pin_added(self, event: Dict[str, Any]) -> None:
        """Handle pin_added events."""
        pass
    
    async def on_pin_removed(self, event: Dict[str, Any]) -> None:
        """Handle pin_removed events."""
        pass
    
    # ===== Reaction Events =====
    
    async def on_reaction_added(self, event: Dict[str, Any]) -> None:
        """Handle reaction_added events."""
        pass
    
    async def on_reaction_removed(self, event: Dict[str, Any]) -> None:
        """Handle reaction_removed events."""
        pass
    
    # ===== Resource Events =====
    
    async def on_resources_added(self, event: Dict[str, Any]) -> None:
        """Handle resources_added events."""
        pass
    
    async def on_resources_removed(self, event: Dict[str, Any]) -> None:
        """Handle resources_removed events."""
        pass
    
    # ===== Scope Events =====
    
    async def on_scope_denied(self, event: Dict[str, Any]) -> None:
        """Handle scope_denied events."""
        pass
    
    async def on_scope_granted(self, event: Dict[str, Any]) -> None:
        """Handle scope_granted events."""
        pass
    
    # ===== Shared Channel Events =====
    
    async def on_shared_channel_invite_accepted(self, event: Dict[str, Any]) -> None:
        """Handle shared_channel_invite_accepted events."""
        pass
    
    async def on_shared_channel_invite_approved(self, event: Dict[str, Any]) -> None:
        """Handle shared_channel_invite_approved events."""
        pass
    
    async def on_shared_channel_invite_declined(self, event: Dict[str, Any]) -> None:
        """Handle shared_channel_invite_declined events."""
        pass
    
    async def on_shared_channel_invite_received(self, event: Dict[str, Any]) -> None:
        """Handle shared_channel_invite_received events."""
        pass
    
    async def on_shared_channel_invite_requested(self, event: Dict[str, Any]) -> None:
        """Handle shared_channel_invite_requested events."""
        pass
    
    # ===== Star Events =====
    
    async def on_star_added(self, event: Dict[str, Any]) -> None:
        """Handle star_added events."""
        pass
    
    async def on_star_removed(self, event: Dict[str, Any]) -> None:
        """Handle star_removed events."""
        pass
    
    # ===== Subteam (User Group) Events =====
    
    async def on_subteam_created(self, event: Dict[str, Any]) -> None:
        """Handle subteam_created events."""
        pass
    
    async def on_subteam_members_changed(self, event: Dict[str, Any]) -> None:
        """Handle subteam_members_changed events."""
        pass
    
    async def on_subteam_self_added(self, event: Dict[str, Any]) -> None:
        """Handle subteam_self_added events."""
        pass
    
    async def on_subteam_self_removed(self, event: Dict[str, Any]) -> None:
        """Handle subteam_self_removed events."""
        pass
    
    async def on_subteam_updated(self, event: Dict[str, Any]) -> None:
        """Handle subteam_updated events."""
        pass
    
    # ===== Team Access Events =====
    
    async def on_team_access_granted(self, event: Dict[str, Any]) -> None:
        """Handle team_access_granted events."""
        pass
    
    async def on_team_access_revoked(self, event: Dict[str, Any]) -> None:
        """Handle team_access_revoked events."""
        pass
    
    # ===== Team Events =====
    
    async def on_team_domain_change(self, event: Dict[str, Any]) -> None:
        """Handle team_domain_change events."""
        pass
    
    async def on_team_join(self, event: Dict[str, Any]) -> None:
        """Handle team_join events."""
        pass
    
    async def on_team_rename(self, event: Dict[str, Any]) -> None:
        """Handle team_rename events."""
        pass
    
    # ===== Token Events =====
    
    async def on_tokens_revoked(self, event: Dict[str, Any]) -> None:
        """Handle tokens_revoked events."""
        pass
    
    # ===== URL Events =====
    
    async def on_url_verification(self, event: Dict[str, Any]) -> None:
        """Handle url_verification events."""
        pass
    
    # ===== User Events =====
    
    async def on_user_change(self, event: Dict[str, Any]) -> None:
        """Handle user_change events."""
        pass
    
    async def on_user_huddle_changed(self, event: Dict[str, Any]) -> None:
        """Handle user_huddle_changed events."""
        pass
    
    async def on_user_resource_denied(self, event: Dict[str, Any]) -> None:
        """Handle user_resource_denied events."""
        pass
    
    async def on_user_resource_granted(self, event: Dict[str, Any]) -> None:
        """Handle user_resource_granted events."""
        pass
    
    async def on_user_resource_removed(self, event: Dict[str, Any]) -> None:
        """Handle user_resource_removed events."""
        pass
    
    # ===== Workflow Events =====
    
    async def on_workflow_deleted(self, event: Dict[str, Any]) -> None:
        """Handle workflow_deleted events."""
        pass
    
    async def on_workflow_published(self, event: Dict[str, Any]) -> None:
        """Handle workflow_published events."""
        pass
    
    async def on_workflow_step_deleted(self, event: Dict[str, Any]) -> None:
        """Handle workflow_step_deleted events."""
        pass
    
    async def on_workflow_step_execute(self, event: Dict[str, Any]) -> None:
        """Handle workflow_step_execute events."""
        pass
    
    async def on_workflow_unpublished(self, event: Dict[str, Any]) -> None:
        """Handle workflow_unpublished events."""
        pass
    
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
        pass
    
    # Private method to resolve the appropriate handler
    
    def _resolve(self, event: Dict[str, Any]) -> Callable[[Dict[str, Any]], Awaitable[None]]:
        """Resolve the appropriate handler method for an event.
        
        This method determines which handler to call based on the event type and subtype.
        
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
