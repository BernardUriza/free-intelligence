# Release Process — fi-runner

Tag-driven release pipeline. Pushing a tag of the form `fi-runner-v<X>.<Y>.<Z>` triggers [`/.github/workflows/publish-fi-runner.yml`](../../../.github/workflows/publish-fi-runner.yml) which:

1. Verifies the tag version matches `fi_runner/__init__.py` `__version__`.
2. Builds an sdist + a `noarch:python` conda package.
3. Creates a GitHub Release with the sdist as asset.
4. `anaconda upload --skip-existing` to https://anaconda.org/bernardurizaorozco/fi-runner.

---

## Pre-release checklist

Before pushing the tag:

- [ ] All work merged to `main` (or to `dev` if you're cutting from there — adjust the publish workflow checkout `ref` if needed).
- [ ] `pyproject.toml` `version` = `fi_runner/__init__.py` `__version__` = intended release.
- [ ] `CHANGELOG.md` has an `[X.Y.Z] — YYYY-MM-DD` entry. Move from `[Unreleased]`.
- [ ] `fi-core` dependency pin in `pyproject.toml` is satisfiable by what's currently on anaconda.org. If you bumped to require a not-yet-published fi-core, **release fi-core first**.
- [ ] Tests pass locally: `cd apps/packages/fi-runner && pytest`.
- [ ] **External-user smoke test from a CLEAN env (see below).**

---

## Cut the release

```bash
# Assume bumping 0.17.1 → 0.17.2 for a patch.

cd apps/packages/fi-runner

# 1. Bump version in pyproject.toml
perl -i -pe 's/^version = "0\.17\.1"/version = "0.17.2"/' pyproject.toml

# 2. Update fi_runner/__init__.py
perl -i -pe 's/^__version__ = "0\.17\.1"/__version__ = "0.17.2"/' fi_runner/__init__.py

# 3. Update CHANGELOG.md
# (Manual: move [Unreleased] entries into a new ## [0.17.2] — YYYY-MM-DD section.)

# 4. Commit + push to dev (the working branch)
cd ../../..  # back to repo root
git add apps/packages/fi-runner/pyproject.toml apps/packages/fi-runner/fi_runner/__init__.py apps/packages/fi-runner/CHANGELOG.md
git commit -m "chore: bump fi-runner to 0.17.2"
git push origin dev

# 5. Open PR dev → main, merge once green
gh pr create --base main --head dev --title "release: fi-runner 0.17.2" --body "..."
# (Wait for green checks + merge.)

# 6. Tag the merged main commit + push tag
git checkout main && git pull
git tag fi-runner-v0.17.2
git push origin fi-runner-v0.17.2
```

The publish workflow then runs. Watch with:

```bash
gh run watch --repo BernardUriza/free-intelligence
```

---

## External-user smoke test (the Golden Rule)

**Before cutting any release, run this from a CLEAN env. If anything fails or requires knowledge not in the README, fix the package or the README first.**

```bash
# Fresh env, no inherited state
conda create -n fi-runner-smoke -y python=3.12
conda activate fi-runner-smoke

# Install ONLY from anaconda.org bernardurizaorozco channel + conda-forge for deps.
# fi-runner depends on fi-core>=0.24,<0.25 — the channel must have a satisfying
# fi-core version. If fi-runner doesn't resolve, fi-core was not published with
# this fi-runner's pin compatible.
conda install -y -c bernardurizaorozco -c conda-forge fi-runner

# Imports the README promises
python -c "
import fi_runner
from fi_runner import Runner, ClaudeCodeBackend, ToolPolicy, PermissionMode
print('fi-runner', fi_runner.__version__)
print('public API OK')
"

# (Optional) actually run a turn with a free fake backend to prove end-to-end:
python -c "
import asyncio
from fi_runner import Runner, ToolPolicy
# Construct a backend via the in-repo testing.fakes if present
# or skip if the README doesn't promise this works without a real harness.
"

# Cleanup
conda deactivate
conda env remove -n fi-runner-smoke -y
```

If any line fails, the release MUST NOT ship until fixed.

---

## After the release

- [ ] Verify on anaconda.org: `anaconda show bernardurizaorozco/fi-runner` lists new version.
- [ ] Verify GitHub Release exists with sdist asset.
- [ ] Test `conda install -c bernardurizaorozco fi-runner=<new>` from a fresh env actually pulls it.
- [ ] If consumers (alice, ferboli, insult — internal) pin `fi-runner>=<old-version>`, ping owners to upgrade.

---

## Hotfix flow

Same as for any package: bump patch, document the bug + fix in CHANGELOG, push tag. Never delete a published artifact, never force-push a tag, never re-publish the same version with different content.

---

## Authoring rules

- One concern per release: do not mix packaging changes with logic refactors.
- The fi-core dependency pin (`fi-core>=0.24,<0.25`) MUST be bumped in lockstep when fi-core releases a new minor. Otherwise consumers get version-resolution headaches.
- Conventional commits: `chore(release):` for the version-bump commit; `feat:` / `fix:` etc. for the work.
