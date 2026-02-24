# Meeting Follow-Up Auto-Draft

Automatically drafts follow-up emails in Gmail after external meetings end in Granola.

## How it works

```
Meeting ends → Granola saves notes → cache file updates
→ macOS LaunchAgent detects change → Python script runs
→ Checks if external → Claude drafts email → Saves to Gmail Drafts
```

## Setup

```bash
chmod +x setup.sh
./setup.sh
```

The setup script will:
1. Check prerequisites (python3, Granola cache, Gmail token)
2. Install Python dependencies (anthropic, google-auth, google-api-python-client)
3. Ask for your Anthropic API key and Rokt email
4. Install the script to `~/.meeting-followup/`
5. Install and load the LaunchAgent

## What you need beforehand

- [x] Google OAuth set up with Gmail API enabled (from your CoWork plugin setup)
- [x] Gmail MCP authenticated (`npx @gongrzhe/server-gmail-autoauth-mcp auth`)
- [x] Granola running on your Mac
- [x] Anthropic API key
- [ ] Gmail token at `~/.gmail-mcp/token.json` (created by the MCP auth flow)

## Important: Gmail Token Format

The MCP auth flow creates a token that the MCP server uses. This script uses the
Google API Python client directly, so it needs a token in the standard Google format.
If the existing token doesn't work, run this one-time auth:

```bash
python3 -c "
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_secrets_file(
    '$HOME/.gmail-mcp/credentials.json',
    ['https://www.googleapis.com/auth/gmail.modify']
)
creds = flow.run_local_server(port=0)
with open('$HOME/.gmail-mcp/token.json', 'w') as f:
    f.write(creds.to_json())
print('Token saved.')
"
```

## Commands

| Action | Command |
|--------|---------|
| Test manually | `python3 ~/.meeting-followup/meeting_followup.py` |
| View logs | `tail -f ~/.meeting-followup/followup.log` |
| Stop | `launchctl unload ~/Library/LaunchAgents/com.matthew.meeting-followup.plist` |
| Start | `launchctl load ~/Library/LaunchAgents/com.matthew.meeting-followup.plist` |
| Check status | `launchctl list \| grep meeting-followup` |

## Troubleshooting

**Draft not appearing:** Check `~/.meeting-followup/followup.log` for errors. Most common: Gmail token expired (re-run auth).

**Firing on internal meetings:** The script checks attendee email domains. If attendees don't have emails in the Granola data, it may misclassify. Check the log output.

**Duplicate drafts:** The script tracks processed meeting IDs in `~/.meeting-followup/state.json`. If you need to reprocess, delete the relevant ID from that file.

**Cache format changed:** If Granola updates their cache format, the script's field-name detection may need updating. Check the log for "No meetings found in cache".
