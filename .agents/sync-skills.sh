#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mode=sync
memory_source=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --check) mode=check; shift ;;
    --memory-source)
      [[ $# -ge 2 ]] || { echo "--memory-source needs a directory" >&2; exit 2; }
      memory_source="$2"; shift 2 ;;
    *) echo "Usage: $0 [--check] [--memory-source DIR]" >&2; exit 2 ;;
  esac
done
if [[ -n "$memory_source" ]]; then
  [[ "$mode" == sync && -f "$memory_source/MEMORY.md" ]] || {
    echo "Memory import requires sync mode and DIR/MEMORY.md" >&2; exit 2;
  }
  mkdir -p "$root/.claude/knowledge/memory"
  rsync -a --include='*.md' --exclude='*' "$memory_source/" "$root/.claude/knowledge/memory/"
fi
options=(-a --delete)
if [[ "$mode" == check ]]; then
  options+=(-n -c -i)
else
  mkdir -p "$root/.agents/skills" "$root/.agents/knowledge"
fi
changes="$(rsync "${options[@]}" \
  --exclude='.venv/' \
  --exclude='.cache/' \
  --exclude='node_modules/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='remote.env' \
  "$root/.claude/skills/" "$root/.agents/skills/")"
if [[ -d "$root/.claude/knowledge" ]]; then
  knowledge_changes="$(rsync "${options[@]}" "$root/.claude/knowledge/" "$root/.agents/knowledge/")"
  changes="${changes}${knowledge_changes}"
fi
if [[ "$mode" == check && -n "$changes" ]]; then
  printf '%s\n' "$changes"
  exit 1
fi
echo "Skills and shared knowledge: $mode OK"
