# Corpus — vultur (crítica de cine)

Generado desde `manifest.yml` con `python scripts/corpus_sync.py lock --persona vultur`.
Los archivos no se versionan; su sha256 sí, en el lock.

| Título | Autor | Año | Origen | Licencia | Obtenido | Archivos |
|---|---|---|---|---|---|---|
| Aesthetic injustice — **por qué:** le pone nombre a algo que él ya sostiene: que descalificarle el gusto a alguien es un daño, no un dictamen | Gustavo H. Dalaqua | 2020 | https://doi.org/10.1080/20004214.2020.1712183 (Journal of Aesthetics & Culture, 12:1) | CC-BY-4.0 (Open access — **CC BY 4.0**, verificada dentro del PDF) | 2026-09-17 | vultur:dalaqua-2020-aesthetic-injustice (sólo en la tienda) |
| Film Theory and Criticism | Leo Braudy y Marshall Cohen (eds.), Oxford University Press | 2009 | PDF local de data/film_corpus_sources/, que ya no está en disco | LicenseRef-Copyright-PrivateRAG (Copyright de la editorial; no se versiona ni se redistribuye) | 2026-06-03 | film:braudy-cohen-2009 (sólo en la tienda) |
| The Language and Style of Film Criticism | no registrado (editorial Routledge) | no registrado | PDF local de data/film_corpus_sources/, que ya no está en disco | LicenseRef-Copyright-PrivateRAG (Copyright de la editorial; no se versiona ni se redistribuye) | 2026-06-03 | film:language-style-criticism (sólo en la tienda) |

Hasta el 2026-09-16 **no se descargaba nada aquí a propósito**: el corpus de
Vultur ya vivía ingerido en producción. El eje ético del issue #61 cambió eso —
ahora sí hay una fuente local, listada abajo.

Nota de descarga: el sitio de la revista rechaza clientes automatizados (403 por
todas las rutas probadas, incluidos tres espejos). El PDF lo bajó Álex desde el
navegador y de ahí se extrajo el texto. La licencia se leyó **dentro del PDF**,
no en la página del editor.

## El corpus de cine, que ya estaba

- **Ubicación viva:** Postgres, namespace `__corpus_film__` — **2,390 chunks**.
- **Fuentes ingeridas** (2026-06-02 / 2026-06-03):
  - Braudy & Cohen (eds.), *Film Theory and Criticism* (Oxford UP, 2009)
  - *The Language and Style of Film Criticism* (Routledge)
- **PDFs originales:** vivían en `data/film_corpus_sources/` (libros con copyright,
  gitignored; ver `data/corpus/../.gitignore` → `data/film_corpus_sources/`).
- **Frame conceptual:** vivía en `khimeras_shared/corpus/film_criticism.md`,
  borrado 2026-09-07 (issue #62, cero llamadores). Recuperable con
  `git show 798ba77:khimeras_shared/corpus/film_criticism.md` si se quiere
  ingerir al namespace; el header vivo es `shared/corpus/headers/vultur.md`.

Los libros fuente son de copyright (átomo de Bernard): NO se re-descargan ni se
versionan; el valor ya está destilado en los embeddings de `__corpus_film__`.
Ver también memoria `project_film_critic_corpus.md`.
