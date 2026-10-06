#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../../.." && pwd)"
source "$REPO/.claude/skills/video-generator/remote.env"
GUARD="$REPO/.claude/skills/pm-production/scripts/server_guard/guard.sh"
PY="${MUSE_SNOW_PY:-~/video-generator/.venv/bin/python}"
WORK="video-resource-videos/work"

if [ $# -lt 2 ]; then
  echo "Dùng: window_snow.sh <clip.mp4> <out.mp4> --window X:Y:W:H [tham số window_snow.py]" >&2
  exit 2
fi
CLIP="$1"; OUT="$2"; shift 2
NAME="$(basename "$OUT" .mp4)"
SSH=(ssh -i "$VG_KEY" -o BatchMode=yes -o ConnectTimeout=10 "$VG_REMOTE")

"${SSH[@]}" "mkdir -p ~/$WORK" || { echo "Không kết nối được server $VG_REMOTE: job chờ, không chạy trên Mac" >&2; exit 1; }
rsync -a -e "ssh -i $VG_KEY -o BatchMode=yes" "$HERE/window_snow.py" "$CLIP" "$VG_REMOTE:$WORK/"
"$GUARD" run "cd ~/$WORK && $PY window_snow.py $(basename "$CLIP") $NAME.mp4 --mask-out $NAME.mask.png $*"
for f in "$NAME.mp4" "$NAME.mask.png"; do
  rsync -a -e "ssh -i $VG_KEY -o BatchMode=yes" "$VG_REMOTE:$WORK/$f" "$(dirname "$OUT")/"
done
echo "đã tải về $(dirname "$OUT")/$NAME.mp4 + $NAME.mask.png"
