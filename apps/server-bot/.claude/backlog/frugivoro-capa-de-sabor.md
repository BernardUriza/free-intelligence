# Frugívoro: capa de datos de sabor y cocina

Status: In progress
Proposed: 2026-11-24 by Bernard ("¿cómo puede reducir los vegetales a sus ingredientes químicos básicos para combinar…?"), investigado con /histerical-search

## What it is

Medido en Postgres el 24-nov-2026: `__corpus_vegan__` tenía 912 chunks y sólo 19 eran de
cocina (Sabores Tapatíos, 20-nov). El resto era ética (Williams 1883, Leach 2023) y nutrición
(dos revisiones PMC). Ver [[frugivoro-persona]]. (Una primera versión de este item decía «858,
cero cocina», copiado del backlog de septiembre sin medir.)

**Hecho el mismo día por orden de Bernard («eso debe cambiar hoy»):** seis artículos CC BY de
química culinaria, 34 artículos de Wikipedia en español y un manual de improvisación propio,
ingeridos a `__corpus_vegan__`. Ver `data/corpus/frugivoro/MANIFEST.md`. Lo que sigue abierto
es la capa de DATOS estructurados (abajo).

Sin corpus, lo gastronómico salía de la memoria del modelo, que es justo donde los LLMs convergen en
muletillas (paprika ahumada en más de la mitad de las recetas "originales" de GPT-4o,
Mizrahi et al. 2025, https://arxiv.org/html/2504.20643v1).

Lo que ya se hizo el mismo día, en la DNA (v4.56.2): corregido el 8× de umami (es con IMP,
animal; en vegetal corre GMP del shiitake seco), método de improvisación por función y
balance, chequeo de muletilla y humor. Esto es la parte de DATOS que la DNA no puede cargar.

## Canonical path to reuse

- La ingesta ya existe: `data/corpus/frugivoro/manifest.yml` + `scripts/corpus_sync.py` + embedder
  e5 local (PR #686). Una fuente nueva es una entrada del manifiesto, `lock`, `plan` y `apply`.
- Como herramienta en vez de corpus: el patrón de capabilities del runner
  (`scripts/sync_capabilities.py`).

## Fuentes evaluadas (24-nov-2026, licencias leídas en el sitio)

| Fuente | Qué da | Licencia | Encaje |
|---|---|---|---|
| USDA FoodData Central | nutrientes por alimento, API 1,000 req/h | CC0 | herramienta de nutrientes; la más limpia |
| FlavorDB2 (IIIT Delhi) | 936 ingredientes → moléculas → descriptores de aroma | CC BY-NC-SA 3.0 | sólo sin fines comerciales; sin descarga masiva, hay que crawlear el JSON por entidad con calma |
| FooDB | +28k compuestos por alimento | uso comercial requiere permiso | último dump de 2020 |
| FlavorGraph (Sony 2020) | embeddings de maridaje | código Apache, datos heredan Recipe1M (NC) | congelado |
| INCMNSZ 2019 (CONABIO) | 3,928 alimentos mexicanos | sin confirmar | complemento local, confirmar licencia antes |

Ojo: el maridaje por compuestos compartidos NO es ley (Spence 2020; Ahn 2011 lo encontró
sólo en cocinas occidentales). FlavorDB sirve para responder "qué aroma tiene esto", no
"qué combina con esto".

## The decision that's the owner's

1. ¿El bot es y será no comercial? Si sí, FlavorDB2 entra; si se monetiza, hay que pedir
   permiso a IIIT Delhi o quedarse en USDA.
2. ¿Corpus (chunks en pgvector) o herramienta (consulta en vivo a USDA)? Recomendación:
   USDA como herramienta (datos vivos, CC0) y un corpus curado de técnica vegetal en español.
3. Qué libros de técnica tiene Bernard en físico o digital para el corpus (McGee, Noma Guide to
   Fermentation, The Flavor Equation, The Vegetarian Flavor Bible): un PDF suyo es material
   de ingesta, scrapear el libro no.

## Status / next step

In progress (24-nov-2026). Bernard decidió: no comercial (entra FlavorDB2) y sin libros por ahora.
Ingeridos como corpus, una ficha por ingrediente con nombre en español: USDA Foundation Foods
(233 vegetales, retirado el mismo día) y FlavorDB2 (581 vegetales). Las cifras vigentes salen de
`python scripts/corpus_sync.py plan --persona frugivoro` y `scripts/corpus_eval.py`.

Hecho (24-nov-2026, v4.60.0, PR #705): `food_lookup`, `nutrient_compare` y `nutrient_rank` sobre
2,031 alimentos vegetales (Foundation 2026-10-29 + SR Legacy 2018-04), montadas sólo en Frugi.
Probado en vivo a las 21:55 UTC: lentejas 3.33 mg de hierro contra frijol negro 2.10, guayaba
2.55 g de proteína, los mismos valores de `persona_core/nutrients/foods.csv`. En la misma
respuesta dijo de memoria «casi tres veces una naranja» (son 3.9): corregido en la DNA, v4.60.1.

Hecho (24-nov-2026, v4.62.4): las 233 fichas USDA salieron del corpus; los 14 casos que las
evaluaban son ahora `test_what_the_usda_cards_answered_the_table_answers`. Los archivos quedaron en
`~/Documents/archive/server-bot-frugivoro-usda-2026-11-24/`.

Hecho (24-nov-2026, v4.62.5): a las 01:08 UTC del 25 Frugi dijo «casi el doble y medio» de 3.33
contra 2.1 (son 1.59). `nutrient_compare` ya entrega la división en cada renglón.

Medido y descartado (24-nov-2026): reranker en otro motor. Xeon 8573C, 2 hilos, 32 preguntas de
Alice × 16 pasajes (mmarco, sentence-transformers 5.7, torch 2.15): torch 2.55 s; ONNX O3 1.78 s con
los mismos resultados (32/32 primeros lugares, 0/512 cruces del piso); OpenVINO 2.45 s; int8 VNNI
1.48 s e int8 OpenVINO 1.17 s, que cambian el primer lugar en 4 y 7 de 32. Los int8 quedan fuera por
calidad. ONNX O3 ahorra ~0.8 s de un turno de ~35 s y agrega onnxruntime + optimum a la imagen: no
entra mientras el turno lo domine el modelo. Si la etapa del corpus vuelve a pesar, es el candidato.

Abierto:
- «queso vegano fermentado de nuez de la india» sigue sin traer el artículo de queso (está en
  inglés): `queso-nuez` en `data/eval/corpus/frugivoro.yml`.
- Frugi infiere sin respaldo que nixtamalizar sube la fibra: los números son reales, la causa no.
