"""Days left on the newest valid TestFlight build of og118. Exit 0 = fine, 3 = renew now, 1 = could not tell.

Usage: ASC_KEY_ID=… ASC_ISSUER_ID=… ASC_PRIVATE_KEY="$(cat AuthKey.p8)" python testflight_caducidad.py [--days 21]
"""
import base64
import datetime
import json
import os
import sys
import time
import urllib.request

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

APP_ID = "6835548280"
API = "https://api.appstoreconnect.apple.com/v1"


def b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def token():
    key = serialization.load_pem_private_key(os.environ["ASC_PRIVATE_KEY"].encode(), None)
    now = int(time.time())
    head = b64(json.dumps({"alg": "ES256", "kid": os.environ["ASC_KEY_ID"], "typ": "JWT"}).encode())
    body = b64(json.dumps({"iss": os.environ["ASC_ISSUER_ID"], "iat": now, "exp": now + 600,
                           "aud": "appstoreconnect-v1"}).encode())
    r, s = utils.decode_dss_signature(key.sign(head + b"." + body, ec.ECDSA(hashes.SHA256())))
    return (head + b"." + body + b"." + b64(r.to_bytes(32, "big") + s.to_bytes(32, "big"))).decode()


def days_left(builds, now):
    valid = [b["attributes"] for b in builds
             if b["attributes"].get("processingState") == "VALID" and not b["attributes"].get("expired")]
    if not valid:
        return None, None
    newest = max(valid, key=lambda a: a["expirationDate"])
    expires = datetime.datetime.fromisoformat(newest["expirationDate"])
    return (expires - now).days, newest["version"]


def main():
    threshold = int(sys.argv[sys.argv.index("--days") + 1]) if "--days" in sys.argv else 21
    url = (API + "/builds?filter[app]=" + APP_ID + "&limit=20&sort=-uploadedDate"
           "&fields[builds]=version,processingState,expirationDate,expired")
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + token()})
    builds = json.load(urllib.request.urlopen(request, timeout=30))["data"]
    left, version = days_left(builds, datetime.datetime.now(datetime.timezone.utc))
    if left is None:
        print("no valid build in TestFlight")
        return 3
    print("build %s expires in %d days (threshold %d)" % (version, left, threshold))
    return 3 if left < threshold else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("could not read TestFlight: %s" % type(exc).__name__)
        sys.exit(1)
