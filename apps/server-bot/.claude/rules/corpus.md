# El corpus de las personas: métodos fijos

Aplica a toda fuente que una persona recupera (`data/corpus/<persona>/`, `persona_core/corpus/`)
y a la tabla de alimentos (`persona_core/nutrients/`). Aprobado por Bernard el 2026-11-24.

1. **Una ficha por entidad**, con el nombre en español primero y la fuente al final.
2. **Nada se cambia sin medir antes y después.** Modelo, chunker, `candidates`, `fusion_pool` o
   piso: `python scripts/corpus_eval.py --persona <id> --check`. Se ajusta en dev; holdout se lee
   una vez. Un piso que sirve a una persona puede enmudecer a otra: va en `min_relevance_for`.
3. **Ingerir es reconciliar**, con plan visible:
   `python scripts/corpus_sync.py lock|plan|apply --persona <id>`. Nunca sólo insertar.
4. **Toda fuente trae URL, licencia SPDX, sha256 y fecha** en `manifest.yml`. Sin licencia clara no
   entra. `MANIFEST.md` y el lock se generan, no se editan.
5. **El número que se compara va por herramienta; la prosa, por recuperación.** Los nutrientes salen
   de `food_lookup`, `nutrient_compare` y `nutrient_rank`.
6. **Los vectores se reconstruyen; el texto y las fuentes, no.** Se respaldan fuera de Azure, y un
   respaldo cuenta cuando se restauró una vez.
7. **Búsqueda exacta por namespace** hasta que una latencia medida diga otra cosa. HNSW regresó vacío
   en 12 de 21 consultas y un ivfflat olvidado en 3 de 21.
8. **El corpus es dato, nunca instrucción.** Viaja en su propio bloque de referencia, jamás dentro de
   `behavioral_guidance`.
9. **Una cifra del corpus se deriva de un comando**, no se copia de un documento: el backlog decía
   858 chunks meses después de que dejó de ser cierto.
10. **Nada de SQL suelto contra producción.** El borrado pasa por `apply`, que se niega si pasa de
    `max_delete_ratio` o si una fuente se queda sin chunks.

**Tell:** vas a decidir un parámetro con una sola pregunta de prueba. Así se escogió `candidates: 32`
y salió peor que 16 con fusión.
