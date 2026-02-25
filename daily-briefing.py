#!/usr/bin/env python3
"""
Granola → Notion Action Item Sync

1. Exports Granola meeting notes to Markdown
2. Reads open (unchecked) items from Notion
3. Sends notes + existing items to Claude → gets only NEW items
4. Pushes new items to Notion as unchecked tasks

Notion is the single source of truth. Check things off there.
Next run automatically respects completed items.
"""

import os
import glob
import json
import hashlib
import subprocess
import requests
from datetime import datetime, timedelta
from anthropic import Anthropic

# ── Config ──────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
DATABASE_ID = "31126a55d11b803cb0fdeeaba6bb2be5"  # <-- Replace with your database ID
NOTES_DIR = os.path.expanduser("~/Documents/granola-daily")

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

CATEGORY_MAP = {
    "action": "Action",
    "follow_up": "Follow-up",
    "decision_pending": "Decision Pending",
    "waiting_on_others": "Waiting on Others",
}

PRIORITY_MAP = {
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}


# ── Notion: Read open items ────────────────────────────────────────────────
def get_open_items():
    """Fetch all unchecked items from Notion."""
    items = []
    has_more = True
    start_cursor = None

    while has_more:
        payload = {
            "filter": {
                "property": "status",
                "checkbox": {"equals": False}
            },
            "page_size": 100
        }
        if start_cursor:
            payload["start_cursor"] = start_cursor

        resp = requests.post(
            f"https://api.notion.com/v1/databases/{DATABASE_ID}/query",
            headers=NOTION_HEADERS,
            json=payload
        )
        data = resp.json()

        for page in data.get("results", []):
            props = page["properties"]
            title_parts = props.get("Name", {}).get("title", [])
            name = title_parts[0]["plain_text"] if title_parts else ""

            item_id_parts = props.get("Item ID", {}).get("rich_text", [])
            item_id = item_id_parts[0]["plain_text"] if item_id_parts else ""

            items.append({
                "notion_page_id": page["id"],
                "description": name,
                "item_id": item_id,
            })

        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor")

    return items


def get_all_item_ids():
    """Fetch ALL item IDs (open + completed) to prevent re-adding completed items."""
    ids = set()
    has_more = True
    start_cursor = None

    while has_more:
        payload = {"page_size": 100}
        if start_cursor:
            payload["start_cursor"] = start_cursor

        resp = requests.post(
            f"https://api.notion.com/v1/databases/{DATABASE_ID}/query",
            headers=NOTION_HEADERS,
            json=payload
        )
        data = resp.json()

        for page in data.get("results", []):
            props = page["properties"]
            item_id_parts = props.get("Item ID", {}).get("rich_text", [])
            if item_id_parts:
                ids.add(item_id_parts[0]["plain_text"])

        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor")

    return ids


# ── Notion: Push new items ─────────────────────────────────────────────────
def push_item_to_notion(item):
    """Create a new page (task) in the Notion database."""
    properties = {
        "Name": {
            "title": [{"text": {"content": item["description"]}}]
        },
        "status": {"checkbox": False},
        "Category": {
            "select": {"name": CATEGORY_MAP.get(item.get("category", "action"), "Action")}
        },
        "Priority": {
            "select": {"name": PRIORITY_MAP.get(item.get("priority", "medium"), "Medium")}
        },
        "Source Meeting": {
            "rich_text": [{"text": {"content": item.get("source_meeting", "")[:2000]}}]
        },
        "Date Added": {
            "date": {"start": datetime.now().strftime("%Y-%m-%d")}
        },
        "Item ID": {
            "rich_text": [{"text": {"content": item["id"]}}]
        },
    }

    if item.get("deadline"):
        properties["Deadline"] = {"date": {"start": item["deadline"]}}

    resp = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json={
            "parent": {"database_id": DATABASE_ID},
            "properties": properties
        }
    )

    if resp.status_code == 200:
        return True
    else:
        print(f"  Error pushing item: {resp.status_code} — {resp.text[:200]}")
        return False


# ── Granola: Get recent notes ──────────────────────────────────────────────
def get_recent_notes(lookback_days=1):
    dates = []
    for i in range(lookback_days + 1):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        dates.append(d)

    notes = []
    for path in sorted(glob.glob(os.path.join(NOTES_DIR, "*.md"))):
        filename = os.path.basename(path)
        if any(filename.startswith(d) for d in dates):
            with open(path, "r") as f:
                notes.append(f"## {filename}\n\n{f.read()}")

    return "\n\n---\n\n".join(notes)


# ── Claude: Extract new items ──────────────────────────────────────────────
def extract_new_items(notes, existing_descriptions):
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    today_str = datetime.now().strftime("%Y-%m-%d")

    existing_block = "\n".join(f"- {d}" for d in existing_descriptions) if existing_descriptions else "(none)"

    prompt = f"""Today is {today_str}. Extract action items from these meeting notes for Matthew DiVincenzo.

MEETING NOTES:
{notes}

ITEMS ALREADY TRACKED (do NOT include these or anything similar):
{existing_block}

Return ONLY a JSON array of NEW items not already tracked above. Each item:
{{
  "description": "concise action item",
  "category": "action|follow_up|decision_pending|waiting_on_others",
  "deadline": "YYYY-MM-DD or null",
  "source_meeting": "meeting title from the filename",
  "priority": "high|medium|low"
}}

Rules:
- Only items that are Matthew's responsibility or that Matthew is waiting on
- Skip anything already covered in the existing items list
- If no new items, return an empty array: []
- Return ONLY valid JSON. No markdown, no explanation, no code fences."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]
    raw = raw.strip()

    try:
        items = json.loads(raw)
        if not isinstance(items, list):
            print("Warning: Claude returned non-list JSON. Skipping.")
            return []
        return items
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse Claude response: {e}")
        print(f"Raw: {raw[:500]}")
        return []


# ── Dedup + ID generation ─────────────────────────────────────────────────
def make_id(description):
    return hashlib.md5(description.lower().strip().encode()).hexdigest()[:8]


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print(f"Granola → Notion Sync — {datetime.now().strftime('%A, %B %d, %Y %I:%M %p')}")
    print("=" * 60)

    # 1. Export Granola notes
    print("\n1. Exporting Granola notes...")
    os.system(
        "source ~/granola-venv/bin/activate && "
        "granola-export export --format markdown "
        f"--output {NOTES_DIR} 2>/dev/null"
    )

    # 2. Read open items from Notion
    print("2. Reading open items from Notion...")
    open_items = get_open_items()
    print(f"   Found {len(open_items)} open item(s) in Notion.")

    # 3. Get ALL item IDs (including completed) to prevent re-adding
    print("3. Fetching all item IDs (including completed)...")
    all_ids = get_all_item_ids()
    print(f"   {len(all_ids)} total item(s) tracked in Notion.")

    # 4. Get today's notes
    print("4. Loading recent meeting notes...")
    notes = get_recent_notes()
    if not notes:
        print("   No meetings found for today/yesterday. Done.")
        return

    # 5. Send to Claude for extraction
    print("5. Asking Claude to extract new items...")
    existing_descs = [item["description"] for item in open_items]
    new_items = extract_new_items(notes, existing_descs)
    print(f"   Claude found {len(new_items)} potential new item(s).")

    # 6. Deduplicate against ALL Notion items (open + completed)
    print("6. Deduplicating and pushing to Notion...")
    pushed = 0
    skipped = 0
    for item in new_items:
        desc = item.get("description", "").strip()
        if not desc:
            continue
        item_id = make_id(desc)
        item["id"] = item_id

        if item_id in all_ids:
            skipped += 1
            continue

        if push_item_to_notion(item):
            pushed += 1
            all_ids.add(item_id)

    print(f"   Pushed {pushed} new item(s) to Notion. Skipped {skipped} duplicate(s).")
    print("\nDone. Check your Notion database.")


if __name__ == "__main__":
    main()
