#!/usr/bin/env python3
"""Promueve los expedientes que vivían dentro del título del chat a objetos.

Hasta ahora el cliente vivía como texto en el título (`fecha — alumno (escuela)
— WhatsApp`). Este script lo lee una vez y lo escribe como expediente con campos
propios, sin perder nada de lo que el equipo ya había capturado a mano.

Es de UNA SOLA VEZ y es idempotente: el store deduplica por `conversacionId`,
así que correrlo dos veces actualiza en vez de duplicar.

    python3 expedientes_desde_titulos.py --api http://localhost:8119 --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request

HUECO = re.compile(r"^(FALTA\b|<.*>$|\[.*\]$|x{3,})", re.I)


def vacio(v: str) -> bool:
    t = (v or "").strip()
    return not t or bool(HUECO.match(t)) or t.upper().startswith("FALTA")


def parse(titulo: str) -> dict:
    partes = [p.strip() for p in re.split(r"\s+—\s+|\s+--\s+|\s+–\s+", titulo)]
    fecha = partes[0] if len(partes) > 1 else ""
    medio = partes[1] if len(partes) > 1 else titulo
    cola = " ".join(partes[2:])

    m = re.match(r"^(.*?)\s*\((.+)\)\s*$", medio)
    alumno = (m.group(1) if m else medio).strip()
    escuela_full = (m.group(2) if m else "").strip()

    # La escuela suele traer el grado pegado: "Urbana 928, 2°A", "Primaria 6°B".
    g = re.search(r"(\d+\s*°\s*[A-Z]?)\s*$", escuela_full)
    grado = g.group(1).strip() if g else ""
    escuela = escuela_full[: g.start()].strip(" ,") if g else escuela_full

    tel = re.search(r"(\d[\d\s]{7,})", cola)
    whatsapp = tel.group(1).strip() if tel else ""

    folio = ""
    f = re.search(r"folio\s*(\d+)", titulo, re.I)
    if f:
        folio = f.group(1)

    return {
        "alumno": "" if vacio(alumno) else alumno,
        "escuela": escuela,
        "grado": grado,
        "whatsapp": "" if vacio(whatsapp) else whatsapp,
        "folio": folio,
        "fecha": fecha,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--api", default="http://localhost:8119")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    with urllib.request.urlopen(f"{args.api}/conversations", timeout=60) as r:
        convs = json.loads(r.read())["conversations"]

    creados = 0
    for c in convs:
        datos = parse(c.get("title") or "")
        # El estado arranca por lo que el expediente ya dice de sí mismo: sin
        # los datos de contacto, la cotización estaba de hecho bloqueada — que
        # es justo lo que la auditoría midió en el 54% de los turnos.
        completo = bool(datos["alumno"]) and bool(datos["whatsapp"])
        expediente = {
            "conversacionId": c["id"],
            "alumno": datos["alumno"],
            "escuela": datos["escuela"],
            "grado": datos["grado"],
            "whatsapp": datos["whatsapp"],
            "folio": datos["folio"],
            "estado": "cotizando" if completo else "bloqueada",
            "notas": f"Importado del título: {c.get('title','')}",
        }
        etiqueta = expediente["alumno"] or "(sin nombre)"
        print(f"  {'✓' if completo else '·'} {etiqueta[:34]:<36} {expediente['escuela'][:24]:<26} {expediente['whatsapp']}")
        if args.dry_run:
            continue
        req = urllib.request.Request(
            f"{args.api}/expedientes",
            data=json.dumps(expediente).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                r.read()
            creados += 1
        except Exception as e:  # noqa: BLE001
            print(f"    ✗ {e}", file=sys.stderr)

    print(f"\n{len(convs)} conversaciones · {creados} expedientes escritos"
          f"{' (dry-run)' if args.dry_run else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
