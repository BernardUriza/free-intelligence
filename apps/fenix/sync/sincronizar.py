#!/usr/bin/env python3
"""Sincroniza el Project de claude.ai ("Servicios Papeleros Fénix") hacia fenix.

Mientras el equipo siga trabajando en claude.ai, esta es la correa de transmisión:
Bernard dice "sincroniza", Claude exporta el estado de claude.ai a un JSON, y este
script decide QUÉ cambió y sube sólo eso.

Es IDEMPOTENTE a propósito. Corre dos veces seguidas y la segunda no hace nada:
cada documento se compara por hash de contenido contra `estado.json`. Sin ese
registro, una sincronización diaria acaba re-subiendo todo o —peor— saltándose en
silencio algo que sí cambió, y nadie se entera hasta que una cotización sale con
un precio viejo.

USO
    # 1. Claude exporta desde el navegador (chrome-devtools sobre claude.ai):
    #      GET /api/organizations/{org}/projects/{proj}/docs   → export.json
    # 2. Este script calcula el delta y lo sube:
    python3 sincronizar.py export.json --api http://localhost:8119 --corpus <id>
    python3 sincronizar.py export.json --dry-run     # sólo dice qué haría
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata
import urllib.request
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ESTADO = AQUI / "estado.json"


def slug(nombre: str) -> str:
    """Nombre de archivo estable para un doc de claude.ai.

    El nombre del doc lleva fecha ("Lista de precios … (14-jul-2026 · actualizada)")
    y esa fecha CAMBIA cuando el equipo lo reescribe. Si el slug dependiera de la
    fecha, cada edición entraría como documento NUEVO y el corpus acabaría con
    cinco listas maestras compitiendo. Por eso se corta en el primer paréntesis:
    el doc conserva su identidad a través de las reescrituras.
    """
    base = nombre.split("(")[0].strip().lower()
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
    limpio = "".join(c if c.isalnum() else "-" for c in base)
    while "--" in limpio:
        limpio = limpio.replace("--", "-")
    return limpio.strip("-")[:60] + ".md"


def cargar_estado() -> dict:
    if ESTADO.exists():
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    return {"docs": {}}


def guardar_estado(estado: dict) -> None:
    ESTADO.write_text(json.dumps(estado, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def subir(api: str, corpus: str, nombre: str, contenido: str) -> dict:
    """Sube un doc al corpus vía multipart, sin dependencias externas."""
    frontera = "----fenixsync"
    cuerpo = (
        f"--{frontera}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{nombre}"\r\n'
        f"Content-Type: text/markdown\r\n\r\n"
        f"{contenido}\r\n"
        f"--{frontera}--\r\n"
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{api}/projects/{corpus}/upload",
        data=cuerpo,
        headers={"Content-Type": f"multipart/form-data; boundary={frontera}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def main() -> int:
    p = argparse.ArgumentParser(description="Sincroniza claude.ai → fenix")
    p.add_argument("export", type=Path, help="JSON exportado de claude.ai (lista de {file_name, content})")
    p.add_argument("--api", default="http://localhost:8119")
    p.add_argument("--corpus", default=None, help="corpus/project id de fenix")
    p.add_argument("--dry-run", action="store_true", help="sólo reporta el delta")
    args = p.parse_args()

    docs = json.loads(args.export.read_text(encoding="utf-8"))
    if not isinstance(docs, list):
        print("El export debe ser una lista de {file_name, content}", file=sys.stderr)
        return 2

    estado = cargar_estado()
    previos = estado.get("docs", {})
    nuevos, cambiados, iguales = [], [], []

    for doc in docs:
        nombre = slug(doc["file_name"])
        h = hashlib.sha256(doc["content"].encode("utf-8")).hexdigest()[:16]
        anterior = previos.get(nombre)
        if anterior is None:
            nuevos.append((nombre, doc, h))
        elif anterior["hash"] != h:
            cambiados.append((nombre, doc, h, anterior))
        else:
            iguales.append(nombre)

    print(f"DELTA · nuevos={len(nuevos)}  cambiados={len(cambiados)}  sin cambio={len(iguales)}")
    for nombre, doc, _ in nuevos:
        print(f"  + NUEVO      {nombre}  ({len(doc['content'])} chars)  ← {doc['file_name'][:52]}")
    for nombre, doc, _, ant in cambiados:
        delta = len(doc["content"]) - ant["chars"]
        print(f"  ~ CAMBIÓ     {nombre}  ({ant['chars']} → {len(doc['content'])} chars, {delta:+d})")
    for nombre in iguales:
        print(f"  = igual      {nombre}")

    if args.dry_run:
        print("\n(dry-run: no se subió nada)")
        return 0
    if not nuevos and not cambiados:
        print("\nNada que sincronizar.")
        return 0
    if not args.corpus:
        print("\nFalta --corpus para subir.", file=sys.stderr)
        return 2

    for nombre, doc, h in nuevos + [(n, d, hh) for n, d, hh, _ in cambiados]:
        res = subir(args.api, args.corpus, nombre, doc["content"])
        previos[nombre] = {
            "hash": h,
            "chars": len(doc["content"]),
            "origen": doc["file_name"],
            "chunks": res.get("chunks"),
        }
        print(f"  ↑ subido {nombre}: {res.get('chunks')} chunks")

    estado["docs"] = previos
    estado["corpus"] = args.corpus
    guardar_estado(estado)
    print(f"\nEstado actualizado en {ESTADO.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
