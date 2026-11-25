# Fichas FlavorDB2 del corpus de Frugi

Estos scripts arman las fichas de ingredientes de `data/corpus/frugivoro/` (una por ingrediente, nombre en español primero). Las fuentes y sus licencias están en el MANIFEST de esa carpeta. Lo descargado va en un directorio aparte, nunca junto a los scripts.

1. `python3 -I crawl_flavordb2.py <dir_json> 1 1000`: baja los JSON de FlavorDB2 uno por uno, con pausa. Corre en cuartos en paralelo si hace falta. Es idempotente: salta los que ya existen.
2. `python3 -I flavordb2_to_corpus.py <dir_json> <dir_cat>`: arma un párrafo por ingrediente, filtra lo animal y agrupa por categoría.
3. `python3 -I split_entries.py <dir_cat> <dir_fichas> <esta_carpeta>`: parte en fichas y les pone el nombre en español de `es_map.py`. Un `MISS` es un nombre que falta en el mapa.
4. Copiar las fichas a `data/corpus/frugivoro/`. Luego `scripts/corpus_sync.py lock --persona frugivoro`, `plan` y `apply`, y `scripts/corpus_eval.py --persona frugivoro --check`.

USDA ya no es corpus: los nutrientes los da `persona_core/nutrients/` (su tabla la arma `scripts/nutrients/build_foods.py`, que usa el mapa `USDA` de `es_map.py`).
