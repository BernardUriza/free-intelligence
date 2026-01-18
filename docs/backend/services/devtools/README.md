# fi-devtools

`fi-devtools` provided the `fi` CLI used in this monorepo to run developer utilities (lint fixers, migrations, inspections, recovery scripts, and CI helpers).

This package has been removed from the main `backend/src` path and archived in `deprecated/fi_devtools_removed_backup` because its functionality is either obsolete or has been migrated to other tools. If you relied on `fi` for local developer tasks, see the "Restore (optional)" section below.

## Restore (optional)

If you still need `fi_devtools` locally, you can restore the archived package (for local use only). From the repository root:

- `mv deprecated/fi_devtools_removed_backup backend/src/fi_devtools`
- `python -m pip install -e backend/src/fi_devtools`

Consider instead using the modernized scripts or CI tasks maintained elsewhere in the repo; consult the team before re-adding the package permanently.

## Usage

The `fi` CLI is not available by default in this checkout. See the "Restore (optional)" section to bring it back locally.

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
