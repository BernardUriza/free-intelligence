#!/usr/bin/env bash
# Install repo-tracked git hooks into .git/hooks/
set -e
ROOT=$(git rev-parse --show-toplevel)
cp "$ROOT/scripts/git-hooks/pre-commit" "$ROOT/.git/hooks/pre-commit"
chmod +x "$ROOT/.git/hooks/pre-commit"
echo "Installed pre-commit hook from scripts/git-hooks/"
