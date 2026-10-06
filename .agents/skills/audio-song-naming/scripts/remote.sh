#!/usr/bin/env bash
set -euo pipefail

SK="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$SK/../../.." && pwd)"
[ -f "$SK/remote.env" ] && source "$SK/remote.env"
: "${QC_REMOTE:?set QC_REMOTE=user@host in $SK/remote.env (mẫu: remote.env.example)}"
HOST="$QC_REMOTE"
KEY="${QC_KEY:-$HOME/.ssh/id_rsa}"
RDIR="${QC_DIR:-youtube-qc}"
SKR=".claude/skills/audio-song-naming"
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=10 "$HOST")
RSH="ssh -i $KEY -o BatchMode=yes -o ConnectTimeout=10"
LIMIT='G=~/youtube-guard/guard.py; if [ -f $G ]; then systemctl --user is-active --quiet youtube-guard || systemd-run --user --unit=youtube-guard --collect -p MemoryMax=256M python3 $G >/dev/null 2>&1; else echo "WARNING: youtube-guard not installed on the server (pm-production/scripts/server_guard/guard.sh install)" >&2; fi; S=~/.config/systemd/user/youtube.slice; [ -f $S ] || { mkdir -p ${S%/*} && printf "[Unit]\nDescription=youtube project: every skill shares this cap (CLAUDE.md)\n[Slice]\nCPUQuota=%s%%\nMemoryHigh=60%%\nMemoryMax=70%%\n" $(( $(nproc) * 60 )) > $S && systemctl --user daemon-reload; }; systemd-run --user --scope --quiet --collect --slice=youtube.slice -- bash -c'

case "${1:-}" in
  setup)
    printf '%s\n' "$SKR/requirements.txt" "$SKR/scripts/whisper_words.py" | rsync -aW --files-from=- -e "$RSH" "$REPO/" "$HOST:$RDIR/"
    "${SSH[@]}" "cd $RDIR && (test -d $SKR/.venv || uv venv -p 3.12 $SKR/.venv) && \
      VIRTUAL_ENV=$SKR/.venv uv pip install -r $SKR/requirements.txt && \
      ($SKR/.venv/bin/python -c 'import torch; assert torch.cuda.is_available()' 2>/dev/null || \
        VIRTUAL_ENV=$SKR/.venv uv pip install --reinstall-package torch 'torch==2.11.0+cu128' \
          --index-url https://download.pytorch.org/whl/cu128) && \
      $SKR/.venv/bin/python -c 'import torch, whisper; print(\"torch\", torch.__version__, \"cuda\", torch.cuda.is_available(), torch.cuda.get_device_name(0), \"whisper\", whisper.__version__)'"
    ;;
  push) rsync -aW --files-from=- -e "$RSH" "$REPO/" "$HOST:$RDIR/" ;;
  exec) "${SSH[@]}" "$LIMIT $(printf %q "cd $RDIR && $2")" ;;
  pull) mkdir -p "$REPO/$2" && rsync -a -e "$RSH" "$HOST:$RDIR/$2/" "$REPO/$2/" ;;
  *) echo "usage: remote.sh setup | push (repo-relative file list on stdin) | exec '<cmd>' | pull <repo-relative dir>" >&2; exit 2 ;;
esac
