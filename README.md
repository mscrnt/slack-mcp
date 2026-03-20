# Slack MCP Server

Standalone Model Context Protocol server for Slack messaging with accountability and papertrail tracking. Built with Python, FastMCP, and slack_sdk.

## Features

- **Send Tool**: `slack_send` - Send messages to users and channels
- **Receive Tools** (optional):
  - `slack_get_messages` - Fetch recent channel messages
  - `slack_get_thread` - Get thread replies
  - `slack_list_channels` - List available channels
  - `slack_search_messages` - Search message history
- **Accountability**: Automatic sender attribution on all messages
- **User Resolution**: Resolves usernames to Slack IDs via email lookup
- **Multi-Recipient**: Send to up to 10 recipients per call
- **Slack Markdown**: Full support for formatting, links, emoji

## Setup

### 1. Configure

Copy `.env.example` to `.env` and set your bot token:

```bash
cp .env.example .env
```

```env
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_EMAIL_DOMAIN=yourdomain.com
MAX_RECIPIENTS=10
ENABLE_RECEIVE=false
MCP_PORT=5000
```

**Required bot scopes for sending:** `chat:write`, `chat:write.public`, `users:read`, `users:read.email`

**Additional scopes for receiving:** `channels:history`, `channels:read`, `search:read`

### 2. Run

#### Docker Compose (recommended)

```bash
docker compose up -d
```

#### Docker

```bash
docker build -t slack-mcp .
docker run -p 5000:5000 --env-file .env slack-mcp
```

#### Standalone

```bash
pip install -r requirements.txt
python server.py
```

The server exposes an SSE endpoint at `http://localhost:5000/sse`.

## Tools

### `slack_send`

Send a Slack message with accountability tracking.

**Parameters:**
- `recipients` (array): Usernames, email addresses, Slack user IDs, or `#channel` names (max 10)
- `message` (string): Message content (supports Slack markdown)
- `sender` (string): Attribution string appended as "— Sent by {sender}"

**Example:**
```json
{
  "recipients": ["jsmith", "#alerts"],
  "message": "Build completed! :tada:",
  "sender": "CI Bot"
}
```

**Returns:**
```json
{
  "success": true,
  "sent": 2,
  "failed": 0,
  "errors": []
}
```

### `slack_get_messages` (requires `ENABLE_RECEIVE=true`)

Fetch recent messages from a channel.

- `channel` (string): Channel name or ID
- `limit` (number): Messages to retrieve (default: 10, max: 100)

### `slack_get_thread` (requires `ENABLE_RECEIVE=true`)

Get all replies in a thread.

- `channel` (string): Channel name or ID
- `thread_ts` (string): Thread timestamp from parent message

### `slack_list_channels` (requires `ENABLE_RECEIVE=true`)

List all available channels with ID, name, privacy, and member count.

### `slack_search_messages` (requires `ENABLE_RECEIVE=true`)

Search messages across channels. Supports Slack search operators:
- `from:username`, `in:#channel`, `has:link`, `after:YYYY-MM-DD`

Parameters:
- `query` (string): Search query
- `count` (number): Results to return (default: 20, max: 100)

## Slack Markdown

- `*bold*`, `_italic_`, `~strikethrough~`
- `` `code` ``, ` ```code block``` `
- `<https://example.com|Link Text>`
- `:tada:` `:rocket:` `:white_check_mark:`

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SLACK_BOT_TOKEN` | Yes | — | Slack Bot OAuth token |
| `SLACK_EMAIL_DOMAIN` | No | `blizzard.com` | Domain for username-to-email resolution |
| `MAX_RECIPIENTS` | No | `10` | Max recipients per message |
| `ENABLE_RECEIVE` | No | `false` | Enable read tools |
| `MCP_PORT` | No | `5000` | SSE server port |

## Integration

Connect to the SSE endpoint from any MCP client:

```
http://localhost:5000/sse
```
