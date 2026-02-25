# Granola → Notion Sync

Extracts action items from Granola meeting notes using Claude API (Haiku) and pushes them to a Notion database.

## How it works
```
Meeting ends → Granola saves notes → cache file updates
→ macOS LaunchAgent detects change → Python script runs
→ Claude extracts action items → Deduplicates → Pushes to Notion
```

## Properties tracked
- Category (Action / Follow-up / Waiting On)
- Priority (High / Medium / Low)
- Deadline
- Source Meeting
- Status (checkbox)

## Setup
Requires: Anthropic API key, Notion API key, Notion database ID.
Run `notion-setup.py` to initialize the database schema.
