#!/usr/bin/env bash
# macOS / Linux / WSL / Git Bash. Creates .venv, installs deps, initializes git.
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -e ".[dev]"
if [ ! -d .git ]; then
  git init -q && git add -A && git commit -qm "Initial commit: job search tool"
fi
echo; echo "Done. Activate with:  source .venv/bin/activate"
