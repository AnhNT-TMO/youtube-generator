#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$root/.agents/skills"
rsync -a --delete \
  --exclude='.venv/' \
  --exclude='.cache/' \
  --exclude='node_modules/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='remote.env' \
  "$root/.claude/skills/" "$root/.agents/skills/"
