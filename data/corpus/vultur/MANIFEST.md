# Corpus — vultur (crítica de cine)

**NO se descargó nada aquí a propósito.** El corpus de Vultur YA está ingerido y
vive en producción.

- **Ubicación viva:** Postgres, namespace `__corpus_film__` — **2,390 chunks**.
- **Fuentes ingeridas** (2026-06-02 / 2026-06-03):
  - Braudy & Cohen (eds.), *Film Theory and Criticism* (Oxford UP, 2009)
  - *The Language and Style of Film Criticism* (Routledge)
- **PDFs originales:** vivían en `data/film_corpus_sources/` (libros con copyright,
  gitignored; ver `data/corpus/../.gitignore` → `data/film_corpus_sources/`).
- **Frame conceptual:** `shared/corpus/film_criticism.md`.

Los libros fuente son de copyright (átomo de Bernard): NO se re-descargan ni se
versionan; el valor ya está destilado en los embeddings de `__corpus_film__`.
Ver también memoria `project_film_critic_corpus.md`.
