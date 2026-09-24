#!/usr/bin/env bash
# Full pipeline for one YouTube URL (runs where it is called; remote.sh calls it on the GPU box).
#   run.sh URL OUT_DIR [--no-qc] [--no-lyrics] [-- extra args for analyze_audio.py]
# OUT_DIR gets: raw/ (media, never commit), audio/ (analysis.json, report.md, qc.json, overview.png),
#               channel.json/.md, thumbnail.jpg, reference.yaml
# Env: QC_PY (python of verification-audio's .venv), QC_TOOLS (dir holding its qc/ package)
set -euo pipefail
SK="$(cd "$(dirname "$0")/.." && pwd)"
PY="$SK/.venv/bin/python"
[ -x "$PY" ] || bash "$SK/scripts/setup.sh"
"$PY" -c "import yaml, librosa, matplotlib" 2>/dev/null || "$SK/.venv/bin/pip" install -q -r "$SK/requirements.txt"
URL="$1"; OUT="$2"; shift 2
QC=1; LYR=(); EXTRA=()
while [ $# -gt 0 ]; do
  case "$1" in
    --no-qc) QC=0; shift ;;
    --no-lyrics) LYR=(--no-lyrics); shift ;;
    --) shift; EXTRA=("$@"); break ;;
    *) echo "unknown arg $1"; exit 1 ;;
  esac
done
RAW="$OUT/raw"; AUD="$OUT/audio"; mkdir -p "$RAW" "$AUD"
# captions are lyric text: on a local run they are deleted on exit, even if a step fails
[ -z "${YTA_ON_SERVER:-}" ] && trap 'rm -f "$RAW"/captions.*.vtt' EXIT
REPO="$(cd "$SK/../../.." && pwd)"
QC_PY="${QC_PY:-$REPO/.claude/skills/verification-audio/.venv/bin/python}"
# stale outputs of earlier runs must never be read as evidence for this run
rm -f "$AUD/qc.json"
HAS_SEG=0
for x in ${EXTRA[@]+"${EXTRA[@]}"}; do
  case "$x" in --single|--segments|--boundaries) HAS_SEG=1 ;; esac
done

# 1. metadata + audio + comments + captions, and the channel's upload list
"$PY" "$SK/scripts/fetch.py" "$URL" "$RAW"
AUDIO=$(ls "$RAW"/audio.* | grep -v -e '\.video_id$' -e '\.part$' | head -1)
"$PY" "$SK/scripts/channel.py" "$RAW/video.info.json" "$OUT" > "$RAW/channel.log" 2>&1 || echo "channel scan failed (see raw/channel.log)"

# 2. song split + per-song length / intro / outro (a video under 10 min is one song, unless a split is given)
DUR=$("$PY" -c "import json; print(int(json.load(open('$RAW/video.info.json')).get('duration') or 0))")
if [ "$DUR" -lt 600 ] && [ "$HAS_SEG" = "0" ]; then
  EXTRA+=(--single); echo "video is ${DUR}s: analysing it as one song (--single)"
fi
CAP=$(ls "$RAW"/captions.en-orig.vtt "$RAW"/captions.en.vtt "$RAW"/captions.*.vtt 2>/dev/null | head -1 || true)
EV=(); [ -n "$CAP" ] && EV+=(--captions "$CAP")
"$PY" "$SK/scripts/analyze_audio.py" "$AUDIO" --info "$RAW/video.info.json" --out "$AUD" \
  ${EV[@]+"${EV[@]}"} ${EXTRA[@]+"${EXTRA[@]}"}
if [ -n "$CAP" ]; then
  "$PY" "$SK/scripts/captions.py" "$CAP" "$AUD/analysis.json" > "$AUD/vocals.md"
else
  echo "no captions (instrumental, or captions disabled)" > "$AUD/vocals.md"
fi

# 3. tempo / voice / instruments / song-1 opening in our QC units (GPU box: Demucs, beat_this, pYIN, AST, Whisper)
if [ "$QC" = "1" ] && [ -x "$QC_PY" ]; then
  "$QC_PY" "$SK/scripts/measure.py" "$OUT" ${LYR[@]+"${LYR[@]}"} || echo "measure failed (reference.yaml will lack tempo/voice)"
elif [ "$QC" = "1" ]; then
  echo "no QC python at $QC_PY: skipping measure.py (set QC_PY or run via remote.sh)"
fi

# 4. reference.yaml
cp "$RAW/thumbnail.jpg" "$OUT/thumbnail.jpg" 2>/dev/null || true
"$PY" "$SK/scripts/build_reference.py" "$OUT" || echo "build_reference failed"
echo "== done: $OUT"
ls -1 "$OUT" "$AUD"
