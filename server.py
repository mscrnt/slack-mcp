#!/usr/bin/env python3
"""
Slack MCP Server

Standalone MCP server for Slack messaging with accountability and papertrail.
Uses the Slack Web API via slack_sdk. Requires SLACK_BOT_TOKEN env var.
"""

import os
import sys

from fastmcp import FastMCP
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# ---------------------------------------------------------------------------
# Token resolution
# ---------------------------------------------------------------------------

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")

if not SLACK_BOT_TOKEN:
    print("ERROR: SLACK_BOT_TOKEN environment variable is required", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Slack client
# ---------------------------------------------------------------------------

slack = WebClient(token=SLACK_BOT_TOKEN)

MAX_RECIPIENTS = int(os.environ.get("MAX_RECIPIENTS", "10"))


def _resolve_user_id(recipient: str) -> str:
    """Resolve a username/email to a Slack user ID."""
    if recipient.startswith("@"):
        return recipient[1:]
    email_domain = os.environ.get("SLACK_EMAIL_DOMAIN", "blizzard.com")
    email = recipient if "@" in recipient else f"{recipient}@{email_domain}"
    resp = slack.users_lookupByEmail(email=email)
    return resp["user"]["id"]


def _resolve_channel_id(channel_name: str) -> str:
    """Resolve a channel name to a Slack channel ID."""
    name = channel_name.lstrip("#")
    # Already an ID
    if name.isalnum() and name == name.upper():
        return name

    cursor = None
    while True:
        resp = slack.conversations_list(
            types="public_channel,private_channel",
            limit=200,
            cursor=cursor,
        )
        for ch in resp.get("channels", []):
            if ch["name"] == name:
                return ch["id"]
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    raise ValueError(f"Channel not found: {channel_name}")


def _resolve_recipient(recipient: str) -> str:
    """Resolve any recipient format to a Slack channel/user ID."""
    if recipient.startswith("#"):
        return _resolve_channel_id(recipient)
    return _resolve_user_id(recipient)


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP("Slack MCP Server")


@mcp.tool()
def slack_send(recipients: list[str], message: str, sender: str) -> dict:
    """Send a Slack message to one or more users or channels.

    Messages include sender attribution for accountability and papertrail tracking.
    Recipients can be Blizzard usernames, email addresses, Slack user IDs, or
    channel names prefixed with #.

    Args:
        recipients: List of usernames or channel names to message.
            Maximum 10 recipients per call to prevent spam.
            Examples: ["username"], ["#tech-pipeline"], ["user1", "user2"]
        message: The message content to send. Supports Slack markdown:
            - *bold*, _italic_, ~strikethrough~
            - `code`, ```code blocks```
            - <url|link text> for links
            - :emoji: for emoji reactions
        sender: Attribution for who/what sent this message. Appended as
            "— Sent by {sender}" to maintain accountability.

    Returns:
        Dictionary with success, sent, failed, and errors fields.

    Example:
        slack_send(
            recipients=["kblossom"],
            message="Your render job completed! :tada:",
            sender="Pipeline Bot"
        )
    """
    if not recipients:
        raise ValueError("At least one recipient is required")
    if len(recipients) > MAX_RECIPIENTS:
        raise ValueError(f"Maximum {MAX_RECIPIENTS} recipients per message")
    if not message or not message.strip():
        raise ValueError("Message cannot be empty")
    if not sender or not sender.strip():
        raise ValueError("Sender attribution is required")

    full_message = f"{message}\n\n_— Sent by {sender}_"

    result = {"success": True, "sent": 0, "failed": 0, "errors": []}

    for recipient in recipients:
        try:
            channel_id = _resolve_recipient(recipient)
            slack.chat_postMessage(
                channel=channel_id,
                text=full_message,
                unfurl_links=True,
                unfurl_media=True,
            )
            result["sent"] += 1
        except (SlackApiError, ValueError) as e:
            result["failed"] += 1
            result["errors"].append(f"Failed to send to {recipient}: {e}")
            result["success"] = False

    return result


if os.environ.get("ENABLE_RECEIVE", "").lower() == "true":

    @mcp.tool()
    def slack_get_messages(channel: str, limit: int = 10) -> list[dict]:
        """Get recent messages from a Slack channel.

        Args:
            channel: Channel name (with or without #) or channel ID
            limit: Number of messages to retrieve (default: 10, max: 100)

        Returns:
            List of messages with text, user, timestamp, and thread info.
        """
        channel_id = _resolve_channel_id(channel)
        resp = slack.conversations_history(channel=channel_id, limit=min(limit, 100))
        return [
            {
                "text": m.get("text"),
                "user": m.get("user"),
                "timestamp": m.get("ts"),
                "thread_ts": m.get("thread_ts"),
                "reply_count": m.get("reply_count", 0),
            }
            for m in resp.get("messages", [])
        ]

    @mcp.tool()
    def slack_get_thread(channel: str, thread_ts: str) -> list[dict]:
        """Get all replies in a Slack thread.

        Args:
            channel: Channel name or ID where the thread exists
            thread_ts: Thread timestamp (from parent message)

        Returns:
            List of messages in the thread with text, user, and timestamp.
        """
        channel_id = _resolve_channel_id(channel)
        resp = slack.conversations_replies(channel=channel_id, ts=thread_ts)
        return [
            {"text": m.get("text"), "user": m.get("user"), "timestamp": m.get("ts")}
            for m in resp.get("messages", [])
        ]

    @mcp.tool()
    def slack_list_channels() -> list[dict]:
        """List all available Slack channels.

        Returns:
            List of channels with id, name, is_private, is_archived, num_members.
        """
        resp = slack.conversations_list()
        return [
            {
                "id": ch["id"],
                "name": ch["name"],
                "is_private": ch["is_private"],
                "is_archived": ch["is_archived"],
                "num_members": ch.get("num_members"),
            }
            for ch in resp.get("channels", [])
        ]

    @mcp.tool()
    def slack_search_messages(query: str, count: int = 20) -> dict:
        """Search for messages across all channels.

        Args:
            query: Search query (supports Slack operators like from:, in:#, has:, after:)
            count: Number of results to return (default: 20, max: 100)

        Returns:
            Dictionary with total count and list of matching messages.
        """
        resp = slack.search_messages(query=query, count=min(count, 100))
        return {
            "total": resp["messages"]["total"],
            "matches": [
                {
                    "text": m.get("text"),
                    "user": m.get("username"),
                    "channel": m.get("channel", {}).get("name"),
                    "timestamp": m.get("ts"),
                    "permalink": m.get("permalink"),
                }
                for m in resp["messages"]["matches"]
            ],
        }


if __name__ == "__main__":
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "5000"))
    print(f"Starting Slack MCP server on {host}:{port}", file=sys.stderr)
    mcp.run(transport="sse", host=host, port=port)
