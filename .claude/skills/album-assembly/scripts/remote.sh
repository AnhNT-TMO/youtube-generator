#!/usr/bin/env bash
set -euo pipefail

SK="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$SK/../../.." && pwd)"
[ -f "$SK/remote.env" ] && source "$SK/remote.env"
: "${QC_REMOTE:?set QC_REMOTE=user@host in $SK/remote.env (mẫu: remote.env.example)}"
HOST="$QC_REMOTE"
KEY="${QC_KEY:-$HOME/.ssh/id_rsa}"
RDIR="${QC_DIR:-youtube-qc}"
SKR=".claude/skills/album-assembly"
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=10 "$HOST")
RSH="ssh -i $KEY -o BatchMode=yes -o ConnectTimeout=10"
LIMIT='S=~/.config/systemd/user/youtube.slice; [ -f $S ] || { mkdir -p ${S%/*} && printf "[Unit]\nDescription=youtube project: every skill shares this cap (CLAUDE.md)\n[Slice]\nCPUQuota=%s%%\nMemoryHigh=60%%\nMemoryMax=70%%\n" $(( $(nproc) * 60 )) > $S && systemctl --user daemon-reload; }; systemd-run --user --scope --quiet --collect --slice=youtube.slice -- bash -c'

push() {
  rsync -aW --delete -e "$RSH" \
    --exclude '.venv/' --exclude '.cache/' --exclude '__pycache__/' --exclude 'remote.env' --exclude 'audio/master/' \
    --exclude 'video/' --exclude '*.mp4' --exclude '*.png' --exclude '*.jpg' --exclude '.DS_Store' \
    --include "$SKR/***" --include '*/' --include '**/albums/**' --include '**/singles/**' --exclude '*' --prune-empty-dirs \
    "$REPO/" "$HOST:$RDIR/"
}

case "${1:-}" in
  setup)
    push
    "${SSH[@]}" "cd $RDIR && (test -d $SKR/.venv || uv venv -p 3.12 $SKR/.venv) && \
      VIRTUAL_ENV=$SKR/.venv uv pip install -r $SKR/requirements.txt && \
      VIRTUAL_ENV=$SKR/.venv uv pip install --reinstall-package torch --reinstall-package torchaudio \
        'torch==2.11.0+cu128' 'torchaudio==2.11.0+cu128' --index-url https://download.pytorch.org/whl/cu128 && \
      $SKR/.venv/bin/python -c 'import torch; print(\"torch\", torch.__version__, \"cuda\", torch.cuda.is_available(), torch.cuda.get_device_name(0))'"
    ;;
  push) push ;;
  exec) "${SSH[@]}" "$LIMIT $(printf %q "cd $RDIR && $2")" ;;
  pull)
    INC=(--include 'assembly.yaml' --include 'assembly.md' --include 'notes/' --include 'notes/assembly-v0.md')
    [ "${3:-}" = master ] && INC+=(--include 'audio/' --include 'audio/master/***')
    rsync -aW -e "$RSH" "${INC[@]}" --exclude '*' "$HOST:$RDIR/$2/" "$REPO/$2/"
    ;;
  *) sed -n 2,10p "$0"; exit 1 ;;
esac
