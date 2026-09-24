#!/usr/bin/env bash
# Run the whole pipeline (download + analysis + QC measurements) on the remote GPU box, then copy the
# results back. Heavy media (audio, per-song WAVs) stays on the server in ~/yt-analyzer/runs/<slug>/raw.
#   remote.sh URL OUT_DIR [--channel-dir channel/<name>] [--idea channel/<name>/ideas/NNN-slug]
#             [run.sh args: --no-qc --no-lyrics] [-- analyze_audio args, e.g. --segments research/<slug>/segments.yaml]
# Config: $SK/remote.env with YTA_REMOTE=user@host, optional YTA_KEY (ssh key).
# The QC stack (verification-audio's scripts/qc + .venv) lives in ~/youtube-qc on the server; its code is
# pushed first (verification-audio/scripts/remote.sh push) so the tempo unit matches verify.py.
set -euo pipefail
SK="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$SK/../../.." && pwd)"
[ -f "$SK/remote.env" ] && source "$SK/remote.env"
: "${YTA_REMOTE:?set YTA_REMOTE=user@host in $SK/remote.env}"
KEY="${YTA_KEY:-$HOME/.ssh/id_rsa}"; QCDIR="${QC_DIR:-youtube-qc}"
RSH="ssh -i $KEY -o BatchMode=yes -o ConnectTimeout=10"
URL="$1"; OUT="$2"; shift 2
SLUG="$(basename "$OUT")"
CHDIR=""; IDEA=""; ARGS=""; SEGS=""
while [ $# -gt 0 ]; do
  case "$1" in
    --channel-dir) CHDIR="$2"; shift 2 ;;   # used locally by build_reference (seed + our baseline)
    --idea) IDEA="$2"; shift 2 ;;
    --segments) SEGS="$2"; ARGS+=" --segments runs/$SLUG/segments.${2##*.}"; shift 2 ;;   # local file -> uploaded below
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
$RSH "$YTA_REMOTE" "cd ~/yt-analyzer && skill/.venv/bin/pip install -q -r skill/requirements.txt >/dev/null 2>&1; \
  QCS=\$HOME/$QCDIR/.claude/skills/verification-audio; \
  QP=\$QCS/.venv/bin/python; QT=\$QCS/scripts; [ -x \$QP ] || { echo 'no QC venv on the server: run .claude/skills/verification-audio/scripts/remote.sh setup'; exit 1; }; \
  YTA_ON_SERVER=1 QC_PY=\$QP QC_TOOLS=\$QT bash skill/scripts/run.sh $(printf %q "$URL") runs/$SLUG$ARGS"
mkdir -p "$OUT"
# outputs a stage may not have produced this time must not survive from an earlier run
rm -f "$OUT/audio/qc.json" "$OUT/reference.yaml"
# results only (allowlist of small text/image outputs; never media)
rsync -a -e "$RSH" --prune-empty-dirs \
  --exclude 'raw/songs/' --exclude '*.vtt' \
  --include '*/' --include '*.md' --include '*.json' --include '*.yaml' --include '*.png' --include '*.jpg' --include '*.log' \
  --exclude '*' \
  "$YTA_REMOTE:yt-analyzer/runs/$SLUG/" "$OUT/"
echo "== results copied to $OUT (media kept on $YTA_REMOTE:~/yt-analyzer/runs/$SLUG/raw)"
# reference.yaml is rebuilt here: our baseline (latest album) and the idea seed read the local channel dir
CH=(); [ -n "$CHDIR" ] && CH=(--channel-dir "$CHDIR")
ID=(); [ -n "$IDEA" ] && ID=(--idea-dir "$IDEA")
"$SK/.venv/bin/python" "$SK/scripts/build_reference.py" "$OUT" ${CH[@]+"${CH[@]}"} ${ID[@]+"${ID[@]}"}
