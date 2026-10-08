#!/usr/bin/env bash
# Run a KQL query against the insult-bot Log Analytics workspace.
# Usage: ./scripts/kql.sh 'ContainerAppConsoleLogs_CL | where ...'
set -euo pipefail
WORKSPACE=14ebd989-62d2-4207-b099-f6e13256fd72
if [ $# -lt 1 ]; then
  echo "Usage: $0 'KQL query'" >&2
  exit 1
fi
QUERY="$1"
TOKEN=$(az account get-access-token --resource https://api.loganalytics.io --query accessToken -o tsv)
curl -s "https://api.loganalytics.io/v1/workspaces/$WORKSPACE/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg q "$QUERY" '{query: $q}')" \
  | python3 -c '
import sys, json, re
d = json.load(sys.stdin)
ansi = re.compile(r"\x1b\[[0-9;]*m")
if "tables" not in d:
    print(json.dumps(d, indent=2))
    sys.exit(0)
for table in d["tables"]:
    cols = [c["name"] for c in table["columns"]]
    print("\t".join(cols))
    for row in table["rows"]:
        # `if v else ""` would turn a real 0 / False / 0.0 into an empty cell —
        # a count of zero must READ as zero, not as missing data.
        cleaned = ["" if v is None else ansi.sub("", str(v)) for v in row]
        print("\t".join(cleaned))
'
