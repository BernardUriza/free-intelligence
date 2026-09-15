# Corpus — unborn_being (NDE/DMT + contra-apologética + crítica al amor)

Fuentes legalmente descargables (dominio público / open access) más un corpus
web extraído para uso privado en el RAG. Los archivos de contenido están
gitignored; este MANIFEST sí se versiona, así que la procedencia viaja con el
repo aunque el texto no.

| Título | Autor | Año | Origen | Licencia / estatus | Filename local |
|---|---|---|---|---|---|
| contraelamor.com — blog completo (379 entradas, 2011–2023) | Agamia / contraelamor.com | 2011–2023 | https://www.contraelamor.com/ (feed JSON de Blogger) | **Copyright del autor** — extraído de la web pública SOLO para el RAG privado de esta persona; no se versiona ni se redistribuye | contraelamor/*.md (379 archivos) |
| DMT Models the Near-Death Experience | Timmermann, Roseman, Williams, Erritzoe, Martial, Cassol, Laureys, Nutt, Carhart-Harris | 2018 | https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2018.01424/pdf | Open access — Frontiers, CC BY | timmermann_2018_dmt_models_nde.pdf |
| The gamma-band activity model of the near-death experience: a critique and a reinterpretation (v2) | Nigel A. Shaw | 2024 | https://f1000research.com/articles/13-674 (v2, PMC PMC11375408) | Open access — F1000Research, CC BY | shaw_2024_gamma_band_nde_critique_v2.pdf |
| Dialogues Concerning Natural Religion | David Hume | 1779 | https://www.gutenberg.org/ebooks/4583 (Plain Text UTF-8) | Dominio público (Project Gutenberg) | hume_dialogues_natural_religion.txt |
| Mistakes of Moses | Robert G. Ingersoll | 1879 | https://www.gutenberg.org/ebooks/38099 (Plain Text UTF-8) | Dominio público (Project Gutenberg) | ingersoll_mistakes_of_moses.txt |
| On the Sufferings of the World (de *Studies in Pessimism*) — **por qué:** el piso del antinatalismo; el sufrimiento no es un accidente del mundo, es su forma de funcionar | Arthur Schopenhauer (trad. T. Bailey Saunders) | 1851 | https://www.gutenberg.org/ebooks/10732 (Plain Text UTF-8) | Dominio público (Project Gutenberg) | schopenhauer_on_the_sufferings_of_the_world.txt |
| On the Vanity of Existence (de *Studies in Pessimism*) — **por qué:** para que Unborn Being pueda discutir qué hace valiosa una vida, no sólo cuánto duele | Arthur Schopenhauer (trad. T. Bailey Saunders) | 1851 | https://www.gutenberg.org/ebooks/10732 (Plain Text UTF-8) | Dominio público (Project Gutenberg) | schopenhauer_on_the_vanity_of_existence.txt |
| Khimeras — `secure_remaining_hazards()`: el hilo del 2026-09-02 | Álex (síntesis con citas), a partir de mensajes de Bernard, Álex e Insult | 2026 | `#general` de Discord (hilo del 2026-09-02 y 2026-09-03), registrado por Álex el 2026-09-15 | Texto propio de esta casa — se versiona en el repo (excepción `!data/corpus/unborn_being/khimeras_*.md` en `.gitignore`) | khimeras_2026-09-02_secure_remaining_hazards.md |

## contraelamor.com — cómo se extrajo y qué falta (2026-07-27)

- **Vía**: el feed JSON de Blogger (`/feeds/posts/default?alt=json`, paginado de
  50 en 50), no raspado de 385 páginas HTML — el feed trae el cuerpo completo de
  cada entrada. El HTML se aplana a párrafos separados por línea en blanco, que
  es exactamente lo que el chunker PARAGRAPH_AWARE del ingestor espera.
- **Un archivo por post**, con `# título`, `Fuente:` (URL canónica) y
  `Publicado:` en el encabezado, de modo que cada `source_ref` recuperado por el
  RAG es citable a su entrada original.
- **Cobertura: 379 de las 385 URLs del sitemap.** Las 6 restantes son entradas
  de SOLO video embebido (iframe de YouTube) con cero texto — verificado una por
  una, no hay nada que extraer:
  `2012/07/blog-post`, `2012/07/blog-post_31`, `2013/04/tuquebuscastu`,
  `2015/12/videoagamia-que-es-agamia`,
  `2016/08/para-que-sirve-la-orientacion-relacional_24`,
  `2016/09/celos-una-idea-sencilla`.
  Si algún día importan, la ruta es transcribir esos videos, no re-raspar.
- **Re-extracción**: el scraper es un script de un solo uso; su lógica está
  descrita arriba y se vuelve a escribir en minutos. Es idempotente por slug.

## Notas de verificación
- El artículo "crítica al modelo gamma" en la URL/PMC indicados es de **Nigel A. Shaw**, no de Martial et al. (Martial es coautora del Timmermann 2018). Se descargó la **v2** (17 Sep 2024, la más reciente, CC BY).
- Ingersoll: la tarea sugería "Some Mistakes of Moses" (#17112); ese id en Gutenberg corresponde a otro título ("Many Thoughts of Many Minds"). El texto canónico de Ingersoll es **"Mistakes of Moses"**, Gutenberg #38099 — verificado por título.

## Pendiente por criterio clínico — decisión de Álex (2026-09-15)

- **"On Suicide"**, el tercer ensayo de *Studies in Pessimism* (mismo Gutenberg
  #10732, mismo dominio público), **NO entra por ahora.** No es un pendiente
  legal: es criterio clínico, y Álex lo quiere revisar con calma antes de
  decidir. El archivo vive FUERA del repo, en
  `Referencias/Filosofia_y_humanidades/schopenhauer-sobre-el-suicidio.txt`.
- Las dos razones medidas contra el código, para que la decisión se pueda
  retomar sin volver a investigarlas:
  1. **Los pasajes se recuperan por parecido con lo que escribe la persona**, y
     **nada apaga el corpus en un turno de crisis**: la guía de seguridad se
     reserva primero y el corpus sólo se cae si esa guía ya llenó el tope
     (`persona_gateway/turn_context.py`), no por ser un turno grave.
  2. **El header de unborn_being obliga a decir de dónde viene lo que usa**, así
     que el pasaje no se leería en silencio: se citaría en voz alta como
     respaldo.
- Lo que SÍ aporta, y por eso no se descarta: es donde Schopenhauer separa
  *dejar de existir* de *no haber empezado nunca* — la distinción
  individuo/especie que Insult marcó como lo único pendiente del hilo del
  2026-09-02.

## Pendientes de copyright (átomo de Bernard — libros de paga, NO descargados)
- Susan Blackmore — *Dying to Live: Near-Death Experiences* (copyright)
- Rick Strassman — *DMT: The Spirit Molecule* (copyright)
- Bruce Greyson — *After* (copyright)
- van Lommel et al. — "Near-death experience in survivors of cardiac arrest", *The Lancet* 2001 (paywalled)
