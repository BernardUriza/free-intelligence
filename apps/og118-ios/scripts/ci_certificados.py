"""A fresh runner has no signing identity, so a signed archive makes Xcode create a development
certificate through the API on every run. `snapshot` records the ones that exist; `prune` revokes
whatever appeared since, so runs do not pile certificates up in the account.

Usage: python ci_certificados.py snapshot|prune <file>   (ASC_* in the environment)
"""
import json
import sys
import urllib.request

from testflight_caducidad import API, token

KINDS = "DEVELOPMENT,IOS_DEVELOPMENT"


def call(method, path):
    request = urllib.request.Request(API + path, method=method, headers={"Authorization": "Bearer " + token()})
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read()
    return json.loads(body) if body else {}


def development_ids():
    data = call("GET", "/certificates?filter[certificateType]=" + KINDS + "&limit=200&fields[certificates]=serialNumber")
    return sorted(item["id"] for item in data["data"])


def main():
    action, path = sys.argv[1], sys.argv[2]
    if action == "snapshot":
        with open(path, "w", encoding="utf-8") as f:
            json.dump(development_ids(), f)
        return 0
    with open(path, encoding="utf-8") as f:
        before = set(json.load(f))
    created = [cid for cid in development_ids() if cid not in before]
    for cid in created:
        call("DELETE", "/certificates/" + cid)
    print("development certificates revoked after the run: %d" % len(created))
    return 0


if __name__ == "__main__":
    sys.exit(main())
