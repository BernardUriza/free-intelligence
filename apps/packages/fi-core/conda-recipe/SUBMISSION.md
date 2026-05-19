# conda-forge submission — fi-core 0.3.0

This directory holds the conda-forge recipe (`meta.yaml`) for submitting
fi-core to the conda-forge community channel.

## What's prepared (in this repo)

- ✅ `fi-core 0.3.0` tagged at [fi-core-v0.3.0](https://github.com/BernardUriza/free-intelligence/releases/tag/fi-core-v0.3.0)
- ✅ GitHub release published with `fi_core-0.3.0.tar.gz` + wheel as assets
- ✅ Source sdist sha256: `96b4cb38c7a3b61afdf6aa0860f108e5ed11874225cb76cf9ab23d9fb41ff3a1`
- ✅ LICENSE file (MIT) at `apps/packages/fi-core/LICENSE`
- ✅ `meta.yaml` recipe drafted in this directory

## Submission steps (manual, ~30 min total)

The conda-forge community channel accepts new packages via PR to the
[`conda-forge/staging-recipes`](https://github.com/conda-forge/staging-recipes)
repo. The PR is reviewed by core maintainers (usually 1-3 weeks, can be
faster if the recipe is clean).

### 1. Fork staging-recipes

```bash
gh repo fork conda-forge/staging-recipes --clone
cd staging-recipes
```

### 2. Create the recipe directory + copy meta.yaml

```bash
mkdir recipes/fi-core
cp /path/to/free-intelligence/apps/packages/fi-core/conda-recipe/meta.yaml recipes/fi-core/
```

### 3. Local lint check (optional but recommended)

```bash
pip install conda-smithy
conda-smithy recipe-lint recipes/fi-core/
```

Fix any warnings the linter surfaces. Common issues:
- Missing `license_file` reference
- Test imports not matching actual module structure
- `noarch: python` declaration when pure-python (it is, in fi-core's case)

### 4. Local rerender (optional)

```bash
conda-smithy rerender
```

This validates the recipe against current conda-forge tooling.

### 5. Open the PR

```bash
git checkout -b add-fi-core
git add recipes/fi-core/
git commit -m "Add fi-core 0.3.0 recipe"
git push origin add-fi-core
gh pr create --base main --head add-fi-core \
  --title "Add fi-core 0.3.0" \
  --body "First submission. fi-core provides LLM primitives extracted from production consumers (AURITY medical RAG, Insult Discord AI persona). See [fi-core-v0.3.0 release](https://github.com/BernardUriza/free-intelligence/releases/tag/fi-core-v0.3.0)."
```

### 6. CI checks + maintainer review

The PR will trigger automated builds on linux-64, osx-64, osx-arm64, and
win-64. All four must pass before maintainer review starts. A bot will
post status updates in the PR comments.

Common feedback to expect:
- Pin `h5py` to a narrower version range
- Add more test imports
- Whether the package should be split into `fi-core` (base) + `fi-core-stores-hdf5` (with h5py) — matches PyPI extras structure
- Maintainer agrees to add @BernardUriza as recipe-maintainer for the feedstock

### 7. Merge → feedstock auto-created

Once merged, conda-forge bots create the dedicated feedstock repo at
`conda-forge/fi-core-feedstock`. Bernard is automatically added as a
maintainer with push access. The first build runs and publishes to
`anaconda.org/conda-forge/fi-core`.

After that, install command becomes:

```bash
conda install -c conda-forge fi-core
```

## Why conda-forge (not PyPI) for fi-core

1. **Compiled binary deps**: h5py + numpy are exactly the kind of C-extension
   dependencies conda manages well. Pure-Python packages can live on PyPI
   without issue, but scientific computing libraries get better dependency
   resolution + binary distribution via conda-forge.
2. **Target audience**: scientific computing / ML / data engineering folks
   who already maintain conda environments for the rest of their stack.
3. **Peer review**: conda-forge submissions go through community-reviewed
   recipe linting + multi-platform CI before merge. Stronger quality signal
   than PyPI's open-publish model.

## Maintenance after first publish

Each new fi-core release (0.3.1, 0.4.0, etc.) requires updating the
feedstock's `meta.yaml`:

1. Tag + release the new version on GitHub (same as 0.3.0 flow)
2. Update `recipes/fi-core/meta.yaml` in the feedstock — bump `version` + new `sha256` + reset `build.number` to 0
3. Open PR on the feedstock repo
4. conda-forge bots auto-merge if the changes are mechanical
5. New build publishes to the channel

Alternatively, the **conda-forge bot** can automate this: it watches the
GitHub release feed and opens PRs to the feedstock automatically. Enable
by adding `conda-forge.yml` configuration after the feedstock exists.
