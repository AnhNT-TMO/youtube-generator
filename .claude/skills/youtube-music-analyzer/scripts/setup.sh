#!/usr/bin/env bash
# One-time setup: private venv with yt-dlp + audio analysis libs. Needs python3, ffmpeg, node.
set -euo pipefail
SK="$(cd "$(dirname "$0")/.." && pwd)"
for bin in python3 ffmpeg node; do command -v $bin >/dev/null || { echo "missing: $bin"; exit 1; }; done
[ -x "$SK/.venv/bin/python" ] || python3 -m venv "$SK/.venv"
"$SK/.venv/bin/pip" install -q --upgrade pip
"$SK/.venv/bin/pip" install -q -r "$SK/requirements.txt"
"$SK/.venv/bin/python" -c "import librosa, yt_dlp, yaml; print('ok: librosa', librosa.__version__, '| yt-dlp', yt_dlp.version.__version__)"
