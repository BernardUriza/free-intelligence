# og118's server keeps seams whose only consumer was Fénix

Status: Proposed
Proposed: 2026-11-17 by Claude, at Fénix's retirement

## What it is

Fénix mounted og118's server as a second consumer. It is gone (`apps/fenix/server` deleted
2026-11-17), and these seams in `apps/og118/server` now have no caller outside og118's own tests:

- `app.create_app(dependencies=...)`, the per-app door.
- `runner.build_runner(persona_text=..., aire_project=..., aire_mode=...)`, a second persona and the
  `agent` mode for the café tutor.
- `FI_PERSONA_PATH`, the env override of the base persona.
- The comments and tests that explain those seams by naming Fénix (`runner.py`, `deps.py`, `app.py`,
  `tests/test_capability_surface_is_bounded.py`, `tests/test_living_claude.py`,
  `tests/test_projects_flag.py`).

## The decision that's the owner's

Delete the seams (og118 is the only consumer and the repo's rule is no dead code), or keep them as
the "1 build, N consumers" shape for a future consumer. `capabilities=` is not in this list: og118's
own tests bound the tool surface through it.

## Status / next step

Nothing started. Deleting is one PR: the three parameters, the env override, their tests.
