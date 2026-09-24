#!/usr/bin/env bash
# Server GPU cho album-assembly: assemble.py tự gọi cho plan / set / render / single (Demucs + beat_this, ghép ~1 giờ audio).
# Dùng chung bản sao repo ~/$QC_DIR trên server với verification-audio (cùng bố cục thư mục).
#
#   $SK/scripts/remote.sh setup                   # lần đầu: đẩy code + tạo venv + cài thư viện trên server
#   $SK/scripts/remote.sh push                    # đẩy code skill + thư mục album/single (text + audio bài) lên server
#   $SK/scripts/remote.sh exec "<lệnh>"           # chạy lệnh trong ~/$QC_DIR trên server
#   $SK/scripts/remote.sh pull <dir-rel> [master] # kéo về assembly.yaml/.md (+ audio/master/ khi có `master`)
#
# Cấu hình: $SK/remote.env (mẫu: remote.env.example) với QC_REMOTE=user@host, QC_KEY (ssh key), QC_DIR.
# Server hiện tại: driver NVIDIA hỗ trợ tối đa CUDA 12.8 → setup cài torch bản cu128.
set -euo pipefail

SK="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$SK/../../.." && pwd)"
[ -f "$SK/remote.env" ] && source "$SK/remote.env"
: "${QC_REMOTE:?set QC_REMOTE=user@host in $SK/remote.env (mẫu: remote.env.example)}"
HOST="$QC_REMOTE"
KEY="${QC_KEY:-$HOME/.ssh/id_rsa}"
RDIR="${QC_DIR:-youtube-qc}"                   # bản sao repo trên server (cùng bố cục thư mục)
SKR=".claude/skills/album-assembly"             # đường dẫn skill, tương đối gốc repo
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=10 "$HOST")
RSH="ssh -i $KEY -o BatchMode=yes -o ConnectTimeout=10"

push() {
  # -W: không tính delta (đỡ CPU máy Mac); audio/master và video không đẩy (master được tạo trên server).
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
  exec) "${SSH[@]}" "cd $RDIR && $2" ;;
  pull)
    INC=(--include 'assembly.yaml' --include 'assembly.md' --include 'notes/' --include 'notes/assembly-v0.md')
    [ "${3:-}" = master ] && INC+=(--include 'audio/' --include 'audio/master/***')
    rsync -aW -e "$RSH" "${INC[@]}" --exclude '*' "$HOST:$RDIR/$2/" "$REPO/$2/"
    ;;
  *) sed -n 2,10p "$0"; exit 1 ;;
esac
