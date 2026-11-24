import json
import sys
import time
import urllib.request
from pathlib import Path

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
FIRST, LAST = int(sys.argv[2]), int(sys.argv[3])
UA = {"User-Agent": "corpus-fetch/1.0 (research; non-commercial)"}
misses = 0
for i in range(FIRST, LAST + 1):
    dest = OUT / f"{i}.json"
    if dest.exists():
        continue
    for attempt in range(4):
        try:
            req = urllib.request.Request(f"https://cosylab.iiitd.edu.in/flavordb2/entities_json?id={i}", headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read()
            break
        except Exception as e:
            body = None
            err = e
            time.sleep(4 * (attempt + 1))
    if body is None:
        print(f"ERR {i} {err}", flush=True)
        continue
    try:
        d = json.loads(body)
    except Exception:
        misses += 1
        print(f"NOJSON {i}", flush=True)
        continue
    if not isinstance(d, dict) or "entity_id" not in d:
        misses += 1
        print(f"EMPTY {i}", flush=True)
        continue
    dest.write_bytes(body)
    print(f"OK {i} {d.get('entity_alias_readable')} [{d.get('category_readable')}] {len(d.get('molecules') or [])}", flush=True)
    time.sleep(0.8)
print("DONE", flush=True)
