"""Dashboard configuration."""

VERSION = "2.1.0"

# Azure Blob Storage URLs (public read access)
BLOB_BASE = "https://insultstorage.blob.core.windows.net/insult-bot"
METRICS_URL = f"{BLOB_BASE}/metrics.json"
LOGS_URL = f"{BLOB_BASE}/logs.json"
TRACES_URL = f"{BLOB_BASE}/traces.json"
FACTS_URL = f"{BLOB_BASE}/facts.json"

# Refresh interval (ms)
REFRESH_INTERVAL = 30_000  # 30 seconds
