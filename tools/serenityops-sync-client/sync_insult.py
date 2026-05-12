"""Push curriculum.yaml + opportunities/structure.yaml to Insult's /sync/serenityops endpoint.

Reads `.env` from the project root for INSULT_SYNC_URL + INSULT_SYNC_TOKEN.
Posts both YAML files as JSON. Exits 0 on success and prints the snapshot
id; exits non-zero with a readable error otherwise.

Standalone — no project deps beyond Python 3.10+. PyYAML is the only
non-stdlib import; we degrade to JSON if it's missing (yamls valid JSON is
rare but the bot accepts a raw JSON body too).
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
CV_PATH = PROJECT_ROOT / "curriculum" / "curriculum.yaml"
PIPELINE_PATH = PROJECT_ROOT / "opportunities" / "structure.yaml"
ENV_PATH = PROJECT_ROOT / ".env"
CLIENT_VERSION = "lite-1.0.0"


def _load_env(path: pathlib.Path) -> dict[str, str]:
    """Tiny .env parser — handles KEY=value, ignores comments/blank lines.
    Avoids pulling in python-dotenv just for two lookups."""
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        out[key.strip()] = val.strip().strip('"').strip("'")
    return out


def _read_yaml(path: pathlib.Path) -> dict | None:
    if not path.exists():
        return None
    try:
        import yaml

        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except ImportError:
        # PyYAML missing — try parsing as JSON (some installs ship the
        # file as JSON for portability). Worst-case: report missing dep.
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(
                "ERROR: PyYAML no está instalado y el archivo no es JSON válido.\nInstala con: pip install pyyaml",
                file=sys.stderr,
            )
            sys.exit(2)


def main() -> int:
    env = _load_env(ENV_PATH)
    url = env.get("INSULT_SYNC_URL") or os.environ.get("INSULT_SYNC_URL")
    token = env.get("INSULT_SYNC_TOKEN") or os.environ.get("INSULT_SYNC_TOKEN")

    if not url or not token:
        print(
            "ERROR: faltan INSULT_SYNC_URL o INSULT_SYNC_TOKEN.\n"
            f"Revisa {ENV_PATH} o tus env vars.\n"
            "Si no tienes token, en Discord escribe `!sync-token` a Insult.",
            file=sys.stderr,
        )
        return 1

    curriculum = _read_yaml(CV_PATH)
    pipeline = _read_yaml(PIPELINE_PATH)

    if curriculum is None and pipeline is None:
        print(
            f"ERROR: no encontré ni {CV_PATH} ni {PIPELINE_PATH}.\n¿Estás corriendo esto desde el folder del proyecto?",
            file=sys.stderr,
        )
        return 1

    payload = {
        "curriculum": curriculum,
        "opportunities": pipeline,
        "client_version": CLIENT_VERSION,
    }
    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(  # noqa: S310 — known endpoint from .env, user-controlled config
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": f"serenityops-sync/{CLIENT_VERSION}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 — known endpoint
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        print(f"ERROR HTTP {e.code}: {body_text}", file=sys.stderr)
        if e.code == 401:
            print(
                "El token no es válido o fue revocado. Genera uno nuevo en Discord con `!sync-token` y actualiza .env.",
                file=sys.stderr,
            )
        return 1
    except urllib.error.URLError as e:
        print(
            f"ERROR de red: {e.reason}\n¿Está caído el bot? Revisa la URL en .env.",
            file=sys.stderr,
        )
        return 1

    snapshot_id = data.get("snapshot_id")
    user_id = data.get("user_id")
    print(
        f"OK — snapshot #{snapshot_id} guardado para user_id={user_id}.\n"
        f"  CV: {'sí' if curriculum else 'no enviado (archivo ausente)'}\n"
        f"  Pipeline: {'sí' if pipeline else 'no enviado (archivo ausente)'}\n"
        "Abre Discord — Insult ya tiene tu estado profesional en contexto."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
