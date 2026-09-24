#!/usr/bin/env bash
# Server GPU cho verification-audio (verify.py check tự gọi) và youtube-music-analyzer (analyzer/scripts/remote.sh gọi `push`).
# Trên server có bản sao repo ~/$QC_DIR cùng bố cục thư mục; chỉ skill này + thư mục album được đẩy lên.
#
#   $SK/scripts/remote.sh setup             # lần đầu: đẩy code + tạo venv + cài thư viện trên server
#   $SK/scripts/remote.sh push              # đẩy code skill + thư mục album lên server
#   $SK/scripts/remote.sh exec "<lệnh>"     # chạy lệnh trong ~/$QC_DIR trên server
#   $SK/scripts/remote.sh pull <album-rel>  # kéo về notes/verify-slot-* của album + cache số đo (json, không kéo stem)
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
SKR=".claude/skills/verification-audio"         # đường dẫn skill, tương đối gốc repo
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=10 "$HOST")
RSH="ssh -i $KEY -o BatchMode=yes -o ConnectTimeout=10"

push() {
  # -W: không tính delta (đỡ CPU máy Mac). Chỉ đẩy thư mục skill (code) và thư mục album (text + audio bài/bản nháp). Không đẩy venv, cache, master, video.
  rsync -aW --delete -e "$RSH" \
    --exclude '.venv/' --exclude '.cache/' --exclude '__pycache__/' --exclude 'remote.env' --exclude 'audio/master/' \
    --exclude 'video/' --exclude '*.mp4' --exclude '*.png' --exclude '.DS_Store' \
    --include "$SKR/***" --include '*/' --include '**/albums/**' --exclude '*' --prune-empty-dirs \
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
    # Chỉ kéo kết quả (text nhỏ). Manifest không kéo về: verify.py ghi manifest ở máy local từ notes/*.json.
    rsync -a -e "$RSH" --include 'verify-slot-*' --exclude '*' "$HOST:$RDIR/$2/notes/" "$REPO/$2/notes/"
    rsync -a -e "$RSH" --prune-empty-dirs --include '*/' --include '*.json' --exclude '*' \
      "$HOST:$RDIR/$SKR/.cache/features/" "$REPO/$SKR/.cache/features/"
    ;;
  *) sed -n 2,10p "$0"; exit 1 ;;
esac
