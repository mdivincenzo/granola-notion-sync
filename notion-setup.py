#!/usr/bin/env python3
"""
One-time setup: Adds required properties to your Notion database.
Run this once, then use daily-briefing.py going forward.
"""

import os
import requests

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
DATABASE_ID = "YOUR_DATABASE_ID_HERE"  # <-- Replace with your database ID

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

update = {
    "properties": {
        "Name": {"title": {}},
        "Status": {"checkbox": {}},
        "Category": {"select": {"options": []}},
        "Priority": {"select": {"options": []}},
        "Deadline": {"date": {}},
        "Source Meeting": {"rich_text": {}},
        "Date Added": {"date": {}},
        "Item ID": {"rich_text": {}},
    }
}

resp = requests.patch(
    f"https://api.notion.com/v1/databases/{DATABASE_ID}",
    headers=headers,
    json=update
)

if resp.status_code == 200:
    print("Database properties configured successfully.")
else:
    print(f"Error {resp.status_code}: {resp.text}")
