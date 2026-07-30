#!/usr/bin/env python3
"""Importa las conversaciones de claude.ai (sesiones Cowork) al store de fenix.

Es el complemento de `sincronizar.py`: aquél trae los DOCUMENTOS del Context,
éste trae el HISTORIAL. Las 33 sesiones con cotizaciones reales dejan de vivir
sólo en claude.ai y aparecen en la barra lateral de fenix, con su hilo completo.

Requiere que fenix use `RemoteConversationLibrary` (el store del servidor). Con
el IndexedDB del navegador esto no serviría: el historial quedaría en la máquina
donde se corrió el script y nadie más lo vería.

Idempotente por el mismo mecanismo que los docs — hash del contenido en
`estado.json`, sección `conversaciones`. Correrlo dos veces no duplica nada.

USO
    python3 importar_conversaciones.py export.json --api http://localhost:8119
    python3 importar_conversaciones.py export.json --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ESTADO = AQUI / "estado.json"
SCHEMA_VERSION = 1


def cargar_estado() -> dict:
    if ESTADO.exists():
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    return {}


def guardar_estado(estado: dict) -> None:
    ESTADO.write_text(json.dumps(estado, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def a_registro(conv: dict) -> dict:
    """Sesión Cowork → ConversationRecord del contrato de fi-core.

    Los mensajes se ordenan por timestamp: el API de eventos no garantiza orden
    de lectura, y un hilo desordenado se lee como una conversación distinta a la
    que ocurrió — el usuario preguntando después de que ya le respondieron.
    """
    mensajes = sorted(conv["messages"], key=lambda m: m.get("timestamp") or "")
    salida = []
    for i, m in enumerate(mensajes):
        msg = {
            "id": f"{conv['id']}-{i}",
            "role": m["role"],
            "content": m["content"],
            "timestamp": m.get("timestamp") or conv["created"],
        }
        # El autor sólo se estampa en las respuestas: en fi-glass el header del
        # bubble lo pinta a partir de este campo, y un mensaje del usuario
        # firmado como "Fénix" invertiría quién dijo qué.
        if m["role"] == "assistant":
            msg["author"] = {"id": "fenix", "name": "Fénix", "symbol": None, "engine": None}
        salida.append(msg)

    primero = next((m["content"] for m in salida if m["role"] == "user"), "")
    return {
        "id": conv["id"],
        "title": conv["title"][:120],
        "titleCustom": True,  # el título viene de claude.ai; no lo regeneres
        "createdAt": conv["created"],
        "updatedAt": conv.get("updated") or conv["created"],
        "messages": salida,
        "preview": primero[:200],
        "schemaVersion": SCHEMA_VERSION,
    }


def subir(api: str, registro: dict) -> None:
    req = urllib.request.Request(
        f"{api}/conversations/{registro['id']}",
        data=json.dumps(registro).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="PUT",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        r.read()


def main() -> int:
    p = argparse.ArgumentParser(description="Importa conversaciones claude.ai → fenix")
    p.add_argument("export", type=Path)
    p.add_argument("--api", default="http://localhost:8119")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    convs = json.loads(args.export.read_text(encoding="utf-8"))
    estado = cargar_estado()
    previos = estado.get("conversaciones", {})

    nuevas, cambiadas, iguales = [], [], []
    for conv in convs:
        reg = a_registro(conv)
        h = hashlib.sha256(json.dumps(reg["messages"], sort_keys=True).encode()).hexdigest()[:16]
        anterior = previos.get(reg["id"])
        if anterior is None:
            nuevas.append((reg, h, conv))
        elif anterior["hash"] != h:
            cambiadas.append((reg, h, conv))
        else:
            iguales.append(reg["id"])

    print(f"DELTA · nuevas={len(nuevas)}  cambiadas={len(cambiadas)}  sin cambio={len(iguales)}")
    for reg, _, conv in nuevas:
        print(f"  + {reg['id'][:24]}  {len(reg['messages']):>3} msgs  {reg['title'][:48]}")
    for reg, _, conv in cambiadas:
        ant = previos[reg["id"]]
        print(f"  ~ {reg['id'][:24]}  {ant['mensajes']} → {len(reg['messages'])} msgs  {reg['title'][:44]}")

    if args.dry_run:
        print("\n(dry-run: no se subió nada)")
        return 0
    if not nuevas and not cambiadas:
        print("\nNada que importar.")
        return 0

    fallos = 0
    for reg, h, _ in nuevas + cambiadas:
        try:
            subir(args.api, reg)
        except urllib.error.HTTPError as e:
            # Un fallo NO se traga: si se registrara en estado.json de todos
            # modos, la siguiente corrida lo daría por importado y esa
            # conversación se perdería en silencio.
            print(f"  ✗ {reg['id'][:24]}: HTTP {e.code} {e.read()[:160].decode(errors='replace')}", file=sys.stderr)
            fallos += 1
            continue
        previos[reg["id"]] = {"hash": h, "mensajes": len(reg["messages"]), "titulo": reg["title"]}
        print(f"  ↑ {reg['id'][:24]}  {len(reg['messages'])} msgs")

    estado["conversaciones"] = previos
    guardar_estado(estado)
    print(f"\nImportadas {len(previos)} conversaciones · fallos: {fallos}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
