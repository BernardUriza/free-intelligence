#!/usr/bin/env zsh

set -euo pipefail

ROOT_DIR=${1:-$PWD}

exclude_patterns=(
  '.git'
  'node_modules'
  '.next'
  '.venv'
  '.idea'
  '.vscode'
  'playwright-report'
  'dist'
  'build'
  'coverage'
  '.svn'
  '.hg'
  '.pytest_cache'
  '.mypy_cache'
  '.ruff_cache'
  'logs'
  'data'
  'apps/aurity/.next'
  'apps/aurity/out'
)

tmp_list=$(mktemp)

pushd "$ROOT_DIR" >/dev/null

# List empty directories excluding common special folders (no eval to avoid zsh parsing issues)
find . -type d \
  \( -name .git -o -name node_modules -o -name .next -o -name .venv -o -name .idea -o -name .vscode -o -name playwright-report -o -name dist -o -name build -o -name coverage -o -name .svn -o -name .hg -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache -o -name logs -o -name data -o -path ./apps/aurity/.next -o -path ./apps/aurity/out \) \
  -prune -o -type d -empty -print | sed 's#^./##' | sort > "$tmp_list"

count=$(wc -l < "$tmp_list")
echo "Found $count empty directories under $ROOT_DIR"

if [[ ${count} -eq 0 ]]; then
  echo "Nothing to delete."
  rm -f "$tmp_list"
  popd >/dev/null
  exit 0
fi

echo "Preview (first 50):"
head -n 50 "$tmp_list" | sed 's/^/  - /'

echo
echo "Deleting empty directories..."
while IFS= read -r dir; do
  # Double-check dir is still empty before removing
  if [[ -d "$dir" ]] && [[ -z $(ls -A "$dir" 2>/dev/null) ]]; then
    rmdir "$dir" || true
  fi
done < "$tmp_list"

echo "Done."

rm -f "$tmp_list"
popd >/dev/null
