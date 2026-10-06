set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${1:?usage: ambient_batch.sh <root with <slug>/track-plan.json> [slug...]}"
shift
SLUGS="${*:-$(ls "$ROOT")}"
for S in $SLUGS; do
  D="$ROOT/$S"
  [ -f "$D/track-plan.json" ] || continue
  for V in ${VIBES:-snowglobe church}; do
    OUT="$D/$S-$V"
    env -u DISPLAY ~/music-tools/venv/bin/python "$HERE/ambient_render.py" "$D/track-plan.json" "$V" "$OUT" 2>&1 | grep -v -E "DPF|assertion" > "$OUT.json"
    M=$(ffmpeg -hide_banner -nostats -i "${OUT}_mix.wav" -af ebur128=peak=true -f null - 2>&1)
    I=$(echo "$M" | awk '/^ +I:/{print $2}' | tail -1)
    TP=$(echo "$M" | awk '/^ +Peak:/{print $2}' | tail -1)
    G=$(python3 -c "print(round(min(-18-$I, -1.6-$TP),2))")
    ffmpeg -y -hide_banner -loglevel error -i "${OUT}_mix.wav" -af volume=${G}dB -c:a libmp3lame -b:a 320k "$OUT.mp3"
    rm -f "${OUT}_mix.wav"
    F=$(ffmpeg -hide_banner -nostats -i "$OUT.mp3" -af ebur128=peak=true -f null - 2>&1 | grep -E "^ +(I|Peak):" | tr -s " " | tr "\n" " ")
    echo "$S $V gain $G |$F| $(cat "$OUT.json" | tail -1 | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["seconds"], d["pass_rms_after"], d["corr_lr"])')"
  done
done
