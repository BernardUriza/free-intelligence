# AGENTS.md — Khimeras (discord-bot)

Convenciones permanentes para agentes de código (codex-cli y otros). Léelas antes
de tocar nada; están aquí para no repetirlas en cada prompt. Si algo en un prompt
contradice esto, **el prompt gana solo para esa tarea** — estas reglas son el default.

## Qué es este repo (post-castigo 2026-07-14)

Bot de Discord multi-persona (Insult, Vultur, Frugívoro, ALICE). El **paquete
`personas/` fue BORRADO** (commit 2f8d9ad, −37,868 líneas) — ya no existe. El
sistema vivo son cuatro paquetes:

- **`persona_gateway/`** — un bot de Discord por persona; recibe, rutea al runner,
  entrega. `gateway.py` es el turn path (`_handle` → `_run_and_deliver`).
- **`persona_runner/`** — FastAPI + Claude Agent SDK. `runner.py` monta routers
  (`api/{turn,judge,workspace,ops}.py`); lógica en `core/`, `engine/`, `routing/`.
  Entrypoint fijo: `uvicorn persona_runner.runner:app`.
- **`khimeras_shared/`** — todo lo compartido: `memory/`, `behavior/` (presets,
  flows, vulnerabilidad — el motor conductual persona-agnóstico), `runner/`
  (clientes HTTP), markers, `guidance.py`, `prompts.py`.
- **`shared/`** — `personas/` (registry + `<id>.md` DNA + `guidance/<id>/` prosa).

**NUNCA importes `personas.` — ese paquete está muerto.** El arnés
`tests/arch/test_import_smoke.py` hace walking-import de todos los módulos: un
import colgante truena la suite. Si crees necesitar `personas.`, estás en el
módulo equivocado; el código vive en uno de los cuatro paquetes de arriba.

## Cómo correr tests y lint — OBLIGATORIO vía conda

El `pytest`/`ruff` del PATH está roto (versión incorrecta que corrompe sintaxis).
La ÚNICA forma válida es a través del env conda `discord-bot`:

```bash
conda run -n discord-bot pytest -q                    # suite completa
conda run -n discord-bot pytest tests/ruta/x.py -q    # un archivo
conda run -n discord-bot ruff check <archivos>        # lint
conda run -n discord-bot ruff format <archivos>       # formato
```

Piso de coverage: 75%. Itera hasta verde + ruff limpio antes de dar algo por hecho.

## Verifica, no asumas (Art. 2 de la constitución del repo)

- Nada "funciona" hasta que corriste el test y VISTE el verde. Pega la salida real
  de `pytest -q` en tu reporte; no narres un resultado que no ejecutaste.
- Si el módulo bajo prueba parece tener un bug, **anótalo en tu reporte, no lo
  arregles** salvo que el prompt te lo pida explícitamente.

## Estilo de tests

pytest plano (jamás `unittest.TestCase`). `def test_...` / `async def test_...`,
cada uno con un docstring de UNA línea de lo que garantiza. Para cada mutador, un
par **positivo + resistencia** (el caso que arregla ⇆ el que NO debe dispararlo).
Mira `tests/agent/` y `tests/core/` antes de escribir. Mockea I/O (asyncpg,
`agent_client`, `judge_client`) con `unittest.mock.AsyncMock`.

## Prompts son contenido, no código (P0)

Un prompt LLM vive en un `.md`, nunca como string inline en `.py`. Prompts de
ENGINE (juzgan al usuario: extracción de facts, juez de consolidación) →
`khimeras_shared/prompts_md/`, cargados con `khimeras_shared.prompts.load_prompt`.
Prosa de la VOZ de una persona → `shared/personas/guidance/<persona_id>/`.

## Git — reglas duras

- **`git commit` SIEMPRE con pathspec explícito**: `git commit -- <ruta1> <ruta2>`.
  NUNCA `git commit` pelón — se lleva TODO el índice, y así un agente se tragó el
  trabajo staged de otro. Verifica con `git diff --cached --name-only` ANTES de
  commitear que no hay nada foráneo en el índice.
- **NUNCA `git push`** — el humano revisa y pushea. Deja tus commits locales.
- **Bump de versión en CADA commit**: sube el patch en `pyproject.toml` (`version`)
  Y en `khimeras_shared/version.py` (`VERSION_TAG`, en superíndices unicode) —
  los dos juntos, mismo commit.
- Mensajes en español, estilo del repo (`feat(...)`, `fix(...)`, `test(...)`).
- No toques archivos fuera del alcance que te dieron.

## Reporte final

Una pantalla: qué archivos tocaste, la salida real de `pytest -q`, el SHA del
commit que dejaste (`git log --oneline -1`), y cualquier bug que hallaste sin
arreglar. Honesto: si algo quedó a medias o sin verificar en real, dilo.
