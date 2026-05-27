# Release Process — fi-core

Tag-driven release pipeline. Pushing a tag of the form `fi-core-v<X>.<Y>.<Z>` triggers [`/.github/workflows/publish-fi-core.yml`](../../../.github/workflows/publish-fi-core.yml) which:

1. Verifies the tag version matches `fi_core/__init__.py` `__version__`.
2. Builds an sdist + a `noarch:python` conda package.
3. Creates a GitHub Release with the sdist as asset.
4. `anaconda upload --skip-existing` to https://anaconda.org/bernardurizaorozco/fi-core.

---

## Pre-release checklist

Before pushing the tag:

- [ ] Work merged to `main` (PR dev → main green + merged).
- [ ] `pyproject.toml` `version` = `fi_core/__init__.py` `__version__` = intended release.
- [ ] `CHANGELOG.md` has an `[X.Y.Z] — YYYY-MM-DD` entry. Move from `[Unreleased]`.
- [ ] Tests pass locally: `cd apps/packages/fi-core && pytest`.
- [ ] **External-user smoke test from a CLEAN env (see below).**

---

## Cut the release

```bash
# Assume bumping 0.24.4 → 0.24.5 (a patch — bugfix).

cd apps/packages/fi-core

# 1. Bump pyproject.toml + __init__.py in lockstep
perl -i -pe 's/^version = "0\.24\.4"/version = "0.24.5"/' pyproject.toml
perl -i -pe 's/^__version__ = "0\.24\.4"/__version__ = "0.24.5"/' fi_core/__init__.py

# 2. Update CHANGELOG.md (move [Unreleased] → ## [0.24.5] — YYYY-MM-DD).

# 3. Commit + push to dev
cd ../../..
git add apps/packages/fi-core/pyproject.toml apps/packages/fi-core/fi_core/__init__.py apps/packages/fi-core/CHANGELOG.md
git commit -m "chore: bump fi-core to 0.24.5"
git push origin dev

# 4. Open PR dev → main, merge once green
gh pr create --base main --head dev --title "release: fi-core 0.24.5" --body "..."

# 5. Tag the merged main commit + push tag
git checkout main && git pull
git tag fi-core-v0.24.5
git push origin fi-core-v0.24.5
```

Watch the run: `gh run watch --repo BernardUriza/free-intelligence`

---

## External-user smoke test (the Golden Rule)

**Before cutting any release, run this from a CLEAN env. If anything fails or requires knowledge not in the README, fix the package or the README first.**

```bash
conda create -n fi-core-smoke -y python=3.12
conda activate fi-core-smoke

# Install bare fi-core (just protocols + types, no heavy deps yet).
conda install -y -c bernardurizaorozco -c conda-forge fi-core

# Public surface promises
python -c "
import fi_core
print('fi-core', fi_core.__version__)
# The package itself only exports __version__ at top level — that's by design.
# Real work imports from submodules:
from fi_core.persona import packs
print('persona packs:', list(packs.GENERIC_AI_DISCLOSURE_EN)[:2])
"

# Optional: smoke an extra. cognitive is dep-free except pyyaml.
conda install -y -c bernardurizaorozco -c conda-forge "fi-core" pyyaml
python -c "
from fi_core.cognitive import available_presets, load_preset
print('presets:', available_presets()[:3])
"

# Cleanup
conda deactivate
conda env remove -n fi-core-smoke -y
```

If any `import` or documented API fails, **the release MUST NOT ship** until fixed.

---

## fi-runner coupling

`fi-runner` declares `fi-core>=0.24,<0.25` in its `pyproject.toml`. When you bump fi-core's MINOR (`0.24.x → 0.25.0`), you also need to ship a fi-runner release that bumps its pin. Otherwise consumers get an unresolvable conda environment.

Order:
1. Release fi-core 0.25.0.
2. Bump fi-runner's pin to `fi-core>=0.25,<0.26`.
3. Release fi-runner 0.18.0 (or appropriate minor bump).

PATCH bumps to fi-core (`0.24.4 → 0.24.5`) are safe — fi-runner's `>=0.24,<0.25` pin satisfies them automatically.

---

## After the release

- [ ] `anaconda show bernardurizaorozco/fi-core` lists the new version.
- [ ] GitHub Release exists with sdist asset.
- [ ] `conda install -c bernardurizaorozco fi-core=<new>` resolves in a fresh env.
- [ ] If you bumped MINOR, follow up with fi-runner release.

---

## Hotfix flow

Same as other packages: bump patch, document the bug + fix in CHANGELOG, push tag. Never delete a published artifact, never force-push a tag, never re-publish the same version with different content.

---

## Authoring rules

- Do NOT mix packaging changes with refactors of fi-core internals.
- The MCP submodules (`fi_core.persona.mcp_server`, `fi_core.cognitive.mcp_server`, etc.) MUST be lazy-loadable — importing `fi_core` without `[mcp]` installed must not raise.
- Conventional commits: `chore(release):` for the version-bump commit; `feat:` / `fix:` etc. for the actual work.
