#!/usr/bin/env python3
"""Rellena el expediente de cada conversación con su desglose, una por una.

Las cotizaciones migradas de claude.ai tienen los renglones escritos en el hilo,
no en campos: por eso no se les puede generar el Excel. Este script le pide al
modelo que lea cada conversación y guarde el desglose con la MISMA herramienta
que usa al cotizar en vivo, para que la reconstrucción y el flujo normal
produzcan la misma forma de dato.

Un turno del modelo por conversación (~80s): es caro, así que va de una en una,
con reporte por línea, y se puede reanudar saltando las ya hechas.

    python3 extraer_cotizaciones.py 5                # las primeras 5
    python3 extraer_cotizaciones.py 99 id1,id2       # todas menos esas
"""
import json, sys, time, urllib.request, urllib.error

API = "http://localhost:8119"
CORPUS = "project-b29d97a1-7c42-4545-ad18-8bc15b25007c"
limite = int(sys.argv[1]) if len(sys.argv) > 1 else 5
saltar = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else set()

convs = json.loads(urllib.request.urlopen(f"{API}/conversations").read())["conversations"]
pendientes = [c for c in convs if c["id"] not in saltar][:limite]

print(f"{len(pendientes)} conversaciones\n")
ok = parcial = sin = err = 0
t0 = time.time()
for i, c in enumerate(pendientes, 1):
    titulo = (c.get("title") or "")[:44]
    inicio = time.time()
    req = urllib.request.Request(
        f"{API}/expedientes/extraer",
        data=json.dumps({"conversacion_id": c["id"], "corpus_id": CORPUS}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    # Reintentos con espera creciente. El límite de la cuenta se reporta como
    # "monthly spend limit" aunque sea transitorio: en el primer lote tumbó 17
    # conversaciones seguidas en 2 segundos cada una, y al reintentar una sola
    # minutos después pasó a la primera. Un lote largo no puede morirse entero
    # por un tope pasajero.
    r = None
    for intento in range(4):
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=600).read())
            break
        except Exception as e:
            if intento == 3:
                raise
            espera = 20 * (intento + 1)
            print(f"       reintento {intento+1}/3 en {espera}s ({str(e)[:40]})", file=sys.stderr)
            time.sleep(espera)
    try:
        assert r is not None
        dur = time.time() - inicio
        if r.get("guardado"):
            ok += 1
            print(f"  {i:>2}/{len(pendientes)} ✓ {dur:>5.0f}s  {titulo}")
        else:
            sin += 1
            print(f"  {i:>2}/{len(pendientes)} · {dur:>5.0f}s  {titulo}  → {(r.get('motivo') or '')[:60]}")
    except Exception as e:
        err += 1
        print(f"  {i:>2}/{len(pendientes)} ✗ {titulo}  → {str(e)[:70]}", file=sys.stderr)

print(f"\nguardadas={ok}  sin cotización={sin}  errores={err}  ({time.time()-t0:.0f}s)")
