#!/usr/bin/env bash
set -euo pipefail
SK="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$SK/../../.." && pwd)"
[ -f "$SK/remote.env" ] && source "$SK/remote.env"
: "${YTA_REMOTE:?set YTA_REMOTE=user@host in $SK/remote.env}"
KEY="${YTA_KEY:-$HOME/.ssh/id_rsa}"; QCDIR="${QC_DIR:-youtube-qc}"
RSH="ssh -i $KEY -o BatchMode=yes -o ConnectTimeout=10"
LIMIT='S=~/.config/systemd/user/youtube.slice; [ -f $S ] || { mkdir -p ${S%/*} && printf "[Unit]\nDescription=youtube project: every skill shares this cap (CLAUDE.md)\n[Slice]\nCPUQuota=%s%%\nMemoryHigh=60%%\nMemoryMax=70%%\n" $(( $(nproc) * 60 )) > $S && systemctl --user daemon-reload; }; systemd-run --user --scope --quiet --collect --slice=youtube.slice -- bash -c'
URL="$1"; OUT="$2"; shift 2
SLUG="$(basename "$OUT")"
CHDIR=""; ARGS=""; SEGS=""
while [ $# -gt 0 ]; do
  case "$1" in
    --channel-dir) CHDIR="$2"; shift 2 ;;
    --segments) SEGS="$2"; ARGS+=" --segments runs/$SLUG/segments.${2##*.}"; shift 2 ;;
    *) ARGS+=" $(printf %q "$1")"; shift ;;
  esac
done

PUSH="$REPO/.claude/skills/verification-audio/scripts/remote.sh"
[ -f "$PUSH" ] || { echo "no QC push script (verification-audio/scripts/remote.sh)"; exit 1; }
bash "$PUSH" push
rsync -a -e "$RSH" --exclude .venv --exclude __pycache__ --exclude remote.env "$SK/" "$YTA_REMOTE:yt-analyzer/skill/"
if [ -n "$SEGS" ]; then
  $RSH "$YTA_REMOTE" "mkdir -p yt-analyzer/runs/$SLUG"
  rsync -a -e "$RSH" "$SEGS" "$YTA_REMOTE:yt-analyzer/runs/$SLUG/segments.${SEGS##*.}"
fi
$RSH "$YTA_REMOTE" "$LIMIT $(printf %q "cd ~/yt-analyzer && skill/.venv/bin/pip install -q -r skill/requirements.txt >/dev/null 2>&1; \
  QCS=\$HOME/$QCDIR/.claude/skills/verification-audio; \
  QP=\$QCS/.venv/bin/python; QT=\$QCS/scripts; [ -x \$QP ] || { echo 'no QC venv on the server: run .claude/skills/verification-audio/scripts/remote.sh setup'; exit 1; }; \
  YTA_ON_SERVER=1 QC_PY=\$QP QC_TOOLS=\$QT bash skill/scripts/run.sh $(printf %q "$URL") runs/$SLUG$ARGS")"
mkdir -p "$OUT"
rm -f "$OUT/audio/qc.json" "$OUT/reference.yaml"
rsync -a -e "$RSH" --prune-empty-dirs \
  --exclude 'raw/songs/' --exclude '*.vtt' \
  --include '*/' --include '*.md' --include '*.json' --include '*.yaml' --include '*.png' --include '*.jpg' --include '*.log' \
  --exclude '*' \
  "$YTA_REMOTE:yt-analyzer/runs/$SLUG/" "$OUT/"
echo "== results copied to $OUT (media kept on $YTA_REMOTE:~/yt-analyzer/runs/$SLUG/raw)"
CH=(); [ -n "$CHDIR" ] && CH=(--channel-dir "$CHDIR")
"$SK/.venv/bin/python" "$SK/scripts/build_reference.py" "$OUT" ${CH[@]+"${CH[@]}"}
