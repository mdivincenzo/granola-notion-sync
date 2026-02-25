# Granola → Notion Sync

Extracts action items from Granola meeting notes using Claude API and pushes them to a Notion database. Notion is the single source of truth — check items off there, and they never resurface.
```
Meeting ends → Granola saves notes → cache file updates
→ macOS LaunchAgent detects change → Python exports notes
→ Reads open items from Notion (deduplicates)
→ Claude extracts only NEW action items → Pushes to Notion
```

## Prerequisites

- macOS
- [Granola](https://granola.ai) installed with at least one recorded meeting
- Python 3.8+
- [Anthropic API key](https://console.anthropic.com)
- [Notion API key](https://www.notion.so/my-integrations) (internal integration)
- [granola-export-tool](https://github.com/haasonsaas/granola-export-tool) installed

## Installation

### Step 1: Clone the repo
```bash
git clone https://github.com/mdivincenzo/granola-notion-sync.git
cd granola-notion-sync
```

### Step 2: Install Python dependencies
```bash
pip3 install anthropic requests --break-system-packages
```

### Step 3: Install the Granola export tool
```bash
pip3 install granola-export-tool --break-system-packages
```

Verify it works:
```bash
granola-export export --format markdown --output ~/Documents/granola-daily
```

### Step 4: Create a Notion integration

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **New integration**
3. Name it, select your workspace
4. Copy the **Internal Integration Secret** (this is your NOTION_API_KEY)
5. Under Capabilities, ensure Read, Insert, and Update content are enabled

### Step 5: Set up the Notion database
```bash
export NOTION_API_KEY="your-notion-key-here"
export ANTHROPIC_API_KEY="your-anthropic-key-here"
python3 notion-setup.py
```

This creates a database with these properties:

| Property | Type | Purpose |
|----------|------|---------|
| Name | Title | Action item description |
| status | Checkbox | Check off when complete |
| Category | Select | Action / Follow-up / Waiting On |
| Priority | Select | High / Medium / Low |
| Deadline | Rich text | Due date or ASAP / None |
| Source Meeting | Rich text | Meeting title |
| Date Added | Date | When the item was synced |
| Item ID | Rich text | Unique hash for deduplication |

Copy the database ID from the URL (32-char string after your workspace name). Update DATABASE_ID in daily-briefing.py.

**Important:** Connect the integration to your database: open the database in Notion, click ⋯ (top right) → Connections → find your integration.

### Step 6: Configure the script
```bash
nano daily-briefing.py
```

Update DATABASE_ID and NOTES_DIR near the top.

### Step 7: Test manually
```bash
export ANTHROPIC_API_KEY="your-key"
export NOTION_API_KEY="your-key"
python3 daily-briefing.py
```

### Step 8: Set up the automatic trigger
```bash
cp com.granola.notion-sync.plist ~/Library/LaunchAgents/
sed -i '' "s|YOUR_USERNAME|$(whoami)|g" ~/Library/LaunchAgents/com.granola.notion-sync.plist
```

Inject API keys:
```bash
/usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:ANTHROPIC_API_KEY string 'your-key'" ~/Library/LaunchAgents/com.granola.notion-sync.plist
/usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:NOTION_API_KEY string 'your-key'" ~/Library/LaunchAgents/com.granola.notion-sync.plist
```

Load:
```bash
launchctl load ~/Library/LaunchAgents/com.granola.notion-sync.plist
```

## Configuration

| Setting | Location | Default |
|---------|----------|---------|
| Database ID | daily-briefing.py line 26 | — |
| Notes directory | daily-briefing.py line 27 | ~/Documents/granola-daily |
| Model | daily-briefing.py line 216 | claude-haiku-4-5-20251001 |
| Throttle interval | plist ThrottleInterval | 120 seconds |

## Troubleshooting

- **"Status is not a property"** — Property names are case-sensitive. Use lowercase "status".
- **"Could not validate API key"** — Check credits at console.anthropic.com.
- **"Unauthorized" from Notion** — Connect integration to database (Step 5).
- **LaunchAgent not firing** — `launchctl unload` then `launchctl load` the plist.

## Logs
```bash
cat /tmp/granola-notion-sync.log
```
