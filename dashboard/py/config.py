"""Dashboard configuration."""

VERSION = "2.2.1"

# Azure Blob Storage URLs (public read access)
STORAGE_BASE = "https://insultstorage.blob.core.windows.net"

# discord-bot (Insult plumbing — primary persona)
BLOB_BASE = f"{STORAGE_BASE}/insult-bot"  # Container name retained as legacy (RENAME-1b)
METRICS_URL = f"{BLOB_BASE}/metrics.json"
LOGS_URL = f"{BLOB_BASE}/logs.json"
TRACES_URL = f"{BLOB_BASE}/traces.json"
FACTS_URL = f"{BLOB_BASE}/facts.json"

# alice-bot (sibling persona — Azure OpenAI gpt-4.1)
ALICE_BLOB_BASE = f"{STORAGE_BASE}/alice-bot"
ALICE_METRICS_URL = f"{ALICE_BLOB_BASE}/metrics.json"
ALICE_LOGS_URL = f"{ALICE_BLOB_BASE}/logs.json"

# Refresh interval (ms)
REFRESH_INTERVAL = 30_000  # 30 seconds
