# Corpus — vultur (crítica de cine)

Hasta el 2026-09-16 **no se descargaba nada aquí a propósito**: el corpus de
Vultur ya vivía ingerido en producción. El eje ético del issue #61 cambió eso —
ahora sí hay una fuente local, listada abajo.

| Título | Autor | Año | Origen | Licencia / estatus | Filename local |
|---|---|---|---|---|---|
| Aesthetic injustice — **por qué:** le pone nombre a algo que él ya sostiene: que descalificarle el gusto a alguien es un daño, no un dictamen | Gustavo H. Dalaqua | 2020 | https://doi.org/10.1080/20004214.2020.1712183 (Journal of Aesthetics & Culture, 12:1) | Open access — **CC BY 4.0**, verificada dentro del PDF | dalaqua_2020_aesthetic_injustice.txt |

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
