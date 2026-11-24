# Frugívoro: capa de datos de sabor y cocina (su corpus hoy no tiene una sola receta)

Status: Proposed
Proposed: 2026-11-24 by Bernard ("¿cómo puede reducir los vegetales a sus ingredientes químicos básicos para combinar…?"), investigado con /histerical-search

## What it is

El corpus `__corpus_vegan__` tiene 858 chunks de tres fuentes: Williams 1883 (ética) y dos
revisiones PMC de nutrición (ver [[frugivoro-persona]]). Cero cocina, cero química del sabor.
Todo lo gastronómico sale de la memoria del modelo, que es justo donde los LLMs convergen en
muletillas (paprika ahumada en más de la mitad de las recetas "originales" de GPT-4o,
Mizrahi et al. 2025, https://arxiv.org/html/2504.20643v1).

Lo que ya se hizo el mismo día, en la DNA (v4.56.2): corregido el 8× de umami (es con IMP,
animal; en vegetal corre GMP del shiitake seco), método de improvisación por función y
balance, chequeo de muletilla y humor. Esto es la parte de DATOS que la DNA no puede cargar.

## Canonical path to reuse

- La ingesta ya existe: `scripts/ingest_corpus.py` + `data/corpus/frugivoro/MANIFEST.md` +
  embedder e5 local (PR #686). Una fuente nueva es una fila en el MANIFEST y una corrida.
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

Proposed. Siguiente paso cuando Bernard decida lo de arriba: una fuente, una ingesta, un probe
con `persona_mcp` pidiendo algo que hoy contesta de memoria.
