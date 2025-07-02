"""
Slack event type definitions.

This module defines the Slack event types as a StrEnum to provide type-safe
references to event types while maintaining string compatibility.
"""

from __future__ import annotations

from enum import StrEnum


class SlackEvent(StrEnum):
    """Enumeration of Slack event types.

    This StrEnum provides type-safe references to Slack event types that
    are also compatible with string operations, since StrEnum inherits from str.

    Event types use the format:
    - Simple events: MESSAGE, REACTION_ADDED, etc.
    - Events with subtypes: MESSAGE_CHANNELS (equivalent to "message.channels")

    The dot notation in Slack's event format (type.subtype) is converted to
    underscore for valid Python identifiers.
    """

    # Standard events
    APP_DELETED = "app_deleted"
    APP_HOME_OPENED = "app_home_opened"
    APP_INSTALLED = "app_installed"
    APP_MENTION = "app_mention"
    APP_RATE_LIMITED = "app_rate_limited"
    APP_REQUESTED = "app_requested"
    APP_UNINSTALLED = "app_uninstalled"
    APP_UNINSTALLED_TEAM = "app_uninstalled_team"
    ASSISTANT_THREAD_CONTEXT_CHANGED = "assistant_thread_context_changed"
    ASSISTANT_THREAD_STARTED = "assistant_thread_started"
    CALL_REJECTED = "call_rejected"
    CHANNEL_ARCHIVE = "channel_archive"
    CHANNEL_CREATED = "channel_created"
    CHANNEL_DELETED = "channel_deleted"
    CHANNEL_HISTORY_CHANGED = "channel_history_changed"
    CHANNEL_ID_CHANGED = "channel_id_changed"
    CHANNEL_LEFT = "channel_left"
    CHANNEL_RENAME = "channel_rename"
    CHANNEL_SHARED = "channel_shared"
    CHANNEL_UNARCHIVE = "channel_unarchive"
    CHANNEL_UNSHARED = "channel_unshared"
    DND_UPDATED = "dnd_updated"
    DND_UPDATED_USER = "dnd_updated_user"
    EMAIL_DOMAIN_CHANGED = "email_domain_changed"
    EMOJI_CHANGED = "emoji_changed"
    FILE_CHANGE = "file_change"
    FILE_COMMENT_ADDED = "file_comment_added"
    FILE_COMMENT_DELETED = "file_comment_deleted"
    FILE_COMMENT_EDITED = "file_comment_edited"
    FILE_CREATED = "file_created"
    FILE_DELETED = "file_deleted"
    FILE_PUBLIC = "file_public"
    FILE_SHARED = "file_shared"
    FILE_UNSHARED = "file_unshared"
    FUNCTION_EXECUTED = "function_executed"
    GRID_MIGRATION_FINISHED = "grid_migration_finished"
    GRID_MIGRATION_STARTED = "grid_migration_started"
    GROUP_ARCHIVE = "group_archive"
    GROUP_CLOSE = "group_close"
    GROUP_DELETED = "group_deleted"
    GROUP_HISTORY_CHANGED = "group_history_changed"
    GROUP_LEFT = "group_left"
    GROUP_OPEN = "group_open"
    GROUP_RENAME = "group_rename"
    GROUP_UNARCHIVE = "group_unarchive"
    IM_CLOSE = "im_close"
    IM_CREATED = "im_created"
    IM_HISTORY_CHANGED = "im_history_changed"
    IM_OPEN = "im_open"
    INVITE_REQUESTED = "invite_requested"
    LINK_SHARED = "link_shared"
    MEMBER_JOINED_CHANNEL = "member_joined_channel"
    MEMBER_LEFT_CHANNEL = "member_left_channel"
    MESSAGE = "message"
    MESSAGE_METADATA_DELETED = "message_metadata_deleted"
    MESSAGE_METADATA_POSTED = "message_metadata_posted"
    MESSAGE_METADATA_UPDATED = "message_metadata_updated"
    PIN_ADDED = "pin_added"
    PIN_REMOVED = "pin_removed"
    REACTION_ADDED = "reaction_added"
    REACTION_REMOVED = "reaction_removed"
    RESOURCES_ADDED = "resources_added"
    RESOURCES_REMOVED = "resources_removed"
    SCOPE_DENIED = "scope_denied"
    SCOPE_GRANTED = "scope_granted"
    SHARED_CHANNEL_INVITE_ACCEPTED = "shared_channel_invite_accepted"
    SHARED_CHANNEL_INVITE_APPROVED = "shared_channel_invite_approved"
    SHARED_CHANNEL_INVITE_DECLINED = "shared_channel_invite_declined"
    SHARED_CHANNEL_INVITE_RECEIVED = "shared_channel_invite_received"
    SHARED_CHANNEL_INVITE_REQUESTED = "shared_channel_invite_requested"
    STAR_ADDED = "star_added"
    STAR_REMOVED = "star_removed"
    SUBTEAM_CREATED = "subteam_created"
    SUBTEAM_MEMBERS_CHANGED = "subteam_members_changed"
    SUBTEAM_SELF_ADDED = "subteam_self_added"
    SUBTEAM_SELF_REMOVED = "subteam_self_removed"
    SUBTEAM_UPDATED = "subteam_updated"
    TEAM_ACCESS_GRANTED = "team_access_granted"
    TEAM_ACCESS_REVOKED = "team_access_revoked"
    TEAM_DOMAIN_CHANGE = "team_domain_change"
    TEAM_JOIN = "team_join"
    TEAM_RENAME = "team_rename"
    TOKENS_REVOKED = "tokens_revoked"
    URL_VERIFICATION = "url_verification"
    USER_CHANGE = "user_change"
    USER_HUDDLE_CHANGED = "user_huddle_changed"
    USER_RESOURCE_DENIED = "user_resource_denied"
    USER_RESOURCE_GRANTED = "user_resource_granted"
    USER_RESOURCE_REMOVED = "user_resource_removed"
    WORKFLOW_DELETED = "workflow_deleted"
    WORKFLOW_PUBLISHED = "workflow_published"
    WORKFLOW_STEP_DELETED = "workflow_step_deleted"
    WORKFLOW_STEP_EXECUTE = "workflow_step_execute"
    WORKFLOW_UNPUBLISHED = "workflow_unpublished"

    # Message subtypes
    MESSAGE_APP_HOME = "message.app_home"
    MESSAGE_CHANNELS = "message.channels"
    MESSAGE_GROUPS = "message.groups"
    MESSAGE_IM = "message.im"
    MESSAGE_MPIM = "message.mpim"

    @classmethod
    def from_type_subtype(cls, event_type: str, subtype: str | None = None) -> SlackEvent:
        """Create a SlackEvent from type and optional subtype.

        Parameters
        ----------
        event_type : str
            The main event type (e.g., 'message')
        subtype : str | None, optional
            The event subtype, if any (e.g., 'channels')

        Returns
        -------
        SlackEvent
            The corresponding SlackEvent enum value

        Raises
        ------
        ValueError
            If the event type (or type.subtype combination) is not defined in the enum
        """
        if subtype:
            # Try to find type.subtype format first
            combined = f"{event_type}.{subtype}"
            try:
                return cls(combined)
            except ValueError:
                pass  # Fall back to just the type

        # Try with just the type
        return cls(event_type)
