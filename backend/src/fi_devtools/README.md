# fi-devtools

`fi-devtools` provides the `fi` CLI used in this monorepo to run developer utilities (lint fixers, migrations, inspections, recovery scripts, and CI helpers).

This package is a thin Typer wrapper around existing legacy scripts in the repository. Most commands accept extra arguments that are forwarded to the underlying script.

## Install (editable, recommended)

From the repository root:

- `python -m pip install -e backend/packages/fi_devtools`

## Usage

- `fi --help`
- `python -m fi_devtools --help`

### Lint

- `fi lint --help`
- `fi lint type-ignores -- --path backend`
- `fi lint remediate-type-errors -- --strict`

### Migrate

- `fi migrate --help`
- `fi migrate jobs-to-tasks`

### Analyze

- `fi analyze --help`
- `fi analyze inspect-h5 -- storage/sessions/<session_id>.h5`

### Recover

- `fi recover --help`
- `fi recover recover-missing-chunks -- --session-id <id>`

### CI

- `fi ci --help`
- `fi ci verify-policy -- --policy config/fi.policy.yaml`

## Notes

- The CLI expects to run from a checkout of this repository (editable install). It locates the repo root by searching for `.git`.
