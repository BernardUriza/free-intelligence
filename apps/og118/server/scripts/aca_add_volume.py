"""Add an Azure Files volume + mount to an exported Container App YAML, in place.

Used by .github/workflows/og118-backend.yml to mount the RAG-store persistence
volume idempotently. It edits the YAML that `az containerapp show -o yaml`
produced so `az containerapp update --yaml` can re-apply it WITH the volume.

Critical: it STRIPS the `configuration.secrets` section. Exported secrets are
redacted to null, and a `--yaml` roundtrip that includes them WIPES the live
secrets (the app would lose ANTHROPIC_API_KEY / the access token). Omission
preserves them. Read-only status fields are stripped too (update rejects them).

Usage: aca_add_volume.py <yaml_path> <volume_name> <storage_name> <mount_path>
"""

from __future__ import annotations

import sys

import yaml

_READONLY_FIELDS = [
    "provisioningState",
    "latestRevisionName",
    "latestReadyRevisionName",
    "latestRevisionFqdn",
    "runningStatus",
    "customDomainVerificationId",
    "eventStreamEndpoint",
    "outboundIpAddresses",
    "delegatedIdentities",
]


def main() -> int:
    yaml_path, volume_name, storage_name, mount_path = sys.argv[1:5]
    doc = yaml.safe_load(open(yaml_path))
    props = doc["properties"]

    props.get("configuration", {}).pop("secrets", None)
    for field in _READONLY_FIELDS:
        props.pop(field, None)
    doc.pop("systemData", None)

    template = props["template"]
    template["volumes"] = [
        {"name": volume_name, "storageType": "AzureFile", "storageName": storage_name}
    ]
    template["containers"][0]["volumeMounts"] = [
        {"volumeName": volume_name, "mountPath": mount_path}
    ]

    yaml.safe_dump(doc, open(yaml_path, "w"), sort_keys=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
