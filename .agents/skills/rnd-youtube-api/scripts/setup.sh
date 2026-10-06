#!/usr/bin/env bash
set -euo pipefail
SK="$(cd "$(dirname "$0")/.." && pwd)"
python3 -m venv "$SK/.venv"
"$SK/.venv/bin/pip" install -q -r "$SK/requirements.txt"
echo "ok: $SK/.venv"
