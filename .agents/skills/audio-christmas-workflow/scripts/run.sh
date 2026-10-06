#!/usr/bin/env bash
set -euo pipefail
tools="$(cd "$(dirname "$0")" && pwd)"
phase="${1:-help}"

usage() {
    cat <<'EOF'
usage: run.sh <phase> [slug] [revision]
  Mac:    sync [slug [revision]]      push tools + WORKFLOW.json (+ plans of slug/revision) to the server
          pull <slug> [revision]      copy the published delivery to ace-steps/christmas-carols/<slug>/<revision> and verify checksums
          record <slug> [revision]    add the pulled delivery to pool-state.json and accent-library/usage.jsonl
          any server phase            forwarded through guard.sh run
  Server: calibrate                   renderer calibration (once)
          refsplit                    rebuild the copy-gate reference set when it is missing
          source <slug> [revision]    MIDI + stems + src_A.wav for every style plan present, buzz + key gate on source
          covers <slug> [revision]    ACE covers, evals, picks, key gate, pick policy per style
          gate <slug> [revision]      re-run picks, key gate and pick policy on existing covers
          status <slug> [revision]    one line per style: pick status
          inspect <slug> [revision]   phase state and recent failure logs
          finish <slug> [revision]    recorded chime + loudness finish into the published delivery
          deliver <slug> [revision]   NGHE_THU, listening map, evidence, verify, checksums
          remix <slug> <parent> <new> <reason...>   re-finish a delivered revision with a mix change
env: CAROL_WORK_ROOT / CAROL_PUBLISHED_ROOT (server, relative to home) and CAROL_PLAN_DIR (Mac plans) override the roots for proof runs
EOF
}

if [ "$(uname)" = Darwin ]; then
    case "$phase" in
    help|-h|--help) usage; exit 0 ;;
    sync|pull) shift; exec python3 "$tools/sync.py" "$phase" "$@" ;;
    record) shift; exec python3 "$tools/record.py" "$@" ;;
    esac
    repo="$(cd "$tools/../../../.." && pwd)"
    guard="$repo/.claude/skills/pm-production/scripts/server_guard/guard.sh"
    remote_tools="$(python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import plan_io; print(plan_io.PIPELINE["server"]["tools"])' "$tools")"
    envs=""
    for name in CAROL_WORK_ROOT CAROL_PUBLISHED_ROOT; do
        if [ -n "${!name:-}" ]; then envs="$envs $name=$(printf %q "${!name}")"; fi
    done
    args=""
    for a in "$@"; do args="$args $(printf %q "$a")"; done
    exec "$guard" run "env$envs bash ~/$remote_tools/run.sh$args"
fi

eval "$(python3 "$tools/plan_io.py")"
export PYTHONPATH="$ACE_HOME:$tools:${PYTHONPATH:-}"
export OMP_NUM_THREADS="$THREADS" OPENBLAS_NUM_THREADS="$THREADS"
config="$tools/WORKFLOW.json"
slug="${2:-}"
revision="${3:-$DEFAULT_REVISION}"
root="$WORK/$slug"
run="$root/$revision-run"
published="$PUBLISHED/$slug/$revision"

need_slug() { test -n "$slug" || { usage; exit 64; }; test -d "$root" || { echo "no $root: run sync from the Mac first"; exit 66; }; }
styles_present() {
    local out=""
    for style in $STYLES; do
        if [ -f "$root/$style/$revision/track-plan.json" ]; then out="$out $style"; fi
    done
    test -n "$out" || { echo "no <style>/$revision/track-plan.json under $root"; exit 66; }
    echo $out
}
lock() {
    exec 8>"/tmp/carol_worker_${1}.lock"
    flock -n 8 || { echo "another carol worker is active for $1"; exit 73; }
}
seal() {
    "$PY_ACE" -c 'import sys, plan_io; from pathlib import Path; plan_io.write_checksums(Path(sys.argv[1]))' "$1"
    echo "PACKAGE_FILES $(find "$1" -type f ! -name checksums.json | wc -l)"
}
pick_and_gate() {
    local work="$1" style="$2"
    "$PY_EVAL" "$tools/select_takes.py" --config "$config" --eval-a "$work/eval_a.json" --eval-b "$work/eval_b.json" --output "$work/picks.json" > "$work/select.log" 2>&1 || test "$?" = 2
    "$PY_ACE" "$tools/key_gate.py" "$work" > "$work/key-gate.log" 2>&1
    "$PY_ACE" "$tools/apply_pick_policy.py" "$work" || { test "$?" = 3; blocked="$blocked $style"; }
}

case "$phase" in
help|-h|--help) usage ;;
calibrate)
    lock calibration
    test ! -e "$CAL" || { echo "$CAL exists"; exit 65; }
    mkdir -p "$CAL"
    flock "$GPU_LOCK" "$PY_RENDER" "$tools/render_raw.py" calibrate "$WORK" "$CAL" > "$CAL/raw-render.log" 2>&1
    "$PY_ACE" "$tools/render_sources.py" calibrate "$WORK" "$CAL" > "$CAL/calibration.log" 2>&1
    tail -n 2 "$CAL/calibration.log"
    ;;
refsplit)
    lock refsplit
    have="$(find "$REFSPLIT_DIR" -name '*_t*.wav' 2>/dev/null | wc -l)"
    if [ "$have" -ge "$REFSPLIT_TRACKS" ]; then echo "REFSPLIT_OK $have tracks"; exit 0; fi
    cd "$ACE_HOME"
    flock "$GPU_LOCK" "$PY_REFSPLIT" refsplit_probe.py $REFSPLIT_VIDEOS
    flock "$GPU_LOCK" "$PY_REFSPLIT" refsplit.py $REFSPLIT_VIDEOS
    have="$(find "$REFSPLIT_DIR" -name '*_t*.wav' | wc -l)"
    test "$have" -ge "$REFSPLIT_TRACKS" || { echo "REFSPLIT_INCOMPLETE $have/$REFSPLIT_TRACKS"; exit 7; }
    echo "REFSPLIT_OK $have tracks"
    ;;
source)
    need_slug; lock "$slug"
    test -f "$CAL/renderer-calibration.json" || { echo "no calibration: run.sh calibrate"; exit 66; }
    if [ -e "$run/raw-source" ]; then
        if [ ! -f "$run/source-checks.json" ]; then
            "$PY_ACE" "$tools/render_sources.py" song "$root" "$revision" "$CAL" > "$run/source.log" 2>&1
        fi
        "$PY_ACE" "$tools/source_resume.py" "$root" "$revision"
        "$PY_EVAL" "$tools/source_buzz.py" "$root" "$revision" > "$run/source-buzz.log" 2>&1 || { cat "$run/source-buzz.log"; echo "SOURCE_BUZZ_FAIL $slug $revision"; exit 4; }
        for style in $(styles_present); do
            "$PY_ACE" "$tools/key_gate.py" "$root/$style/$revision" > "$root/$style/$revision/source-key-check.log" 2>&1
        done
        cat "$run/source-buzz.log"
        grep -h method_valid "$root"/*/"$revision"/source-key-check.log | cut -c1-300
        echo "SOURCE_RESUMED $slug $revision"
        exit 0
    fi
    "$PY_RENDER" "$tools/render_raw.py" song "$root" "$revision" > "$root/raw-render.log" 2>&1
    mv "$root/raw-render.log" "$run/raw-render.log"
    "$PY_ACE" "$tools/render_sources.py" song "$root" "$revision" "$CAL" > "$run/source.log" 2>&1
    "$PY_EVAL" "$tools/source_buzz.py" "$root" "$revision" > "$run/source-buzz.log" 2>&1 || { cat "$run/source-buzz.log"; echo "SOURCE_BUZZ_FAIL $slug $revision"; exit 4; }
    for style in $(styles_present); do
        "$PY_ACE" "$tools/key_gate.py" "$root/$style/$revision" > "$root/$style/$revision/source-key-check.log" 2>&1
    done
    cat "$run/source-buzz.log"
    grep -h method_valid "$root"/*/"$revision"/source-key-check.log | cut -c1-300
    echo "SOURCE_COMPLETE $slug $revision"
    ;;
covers)
    need_slug; lock "$slug"
    test -f "$run/source-checks.json" || { echo "no sources: run.sh source $slug $revision"; exit 66; }
    have="$(find "$REFSPLIT_DIR" -name '*_t*.wav' 2>/dev/null | wc -l)"
    test "$have" -ge "$REFSPLIT_TRACKS" || { echo "copy-gate reference set missing ($have/$REFSPLIT_TRACKS): run.sh refsplit"; exit 66; }
    blocked=""
    for style in $(styles_present); do
        work="$root/$style/$revision"
        "$PY_ACE" "$tools/cover_takes.py" "$work" --config "$config" --stage revision --spec "$work/track-plan.json" > "$work/cover.log" 2>&1
        flock "$GPU_LOCK" "$PY_EVAL" "$tools/carol_eval_a.py" "$work" > "$work/eval-a.log" 2>&1
        flock "$GPU_LOCK" "$PY_VOCAL" "$tools/vocal_check.py" "$work/src_A.wav" "$work"/cov_*.flac > "$work/eval_b.json" 2> "$work/eval-b.log"
        pick_and_gate "$work" "$style"
        echo "EVALUATION_COMPLETE $slug $style $revision"
    done
    if [ -n "$blocked" ]; then echo "BLOCKED_STYLES $slug $revision$blocked"; fi
    ;;
gate)
    need_slug; lock "$slug"
    blocked=""
    for style in $(styles_present); do
        work="$root/$style/$revision"
        test -f "$work/eval_a.json" -a -f "$work/eval_b.json" || { echo "no evals in $work: run.sh covers"; exit 66; }
        pick_and_gate "$work" "$style"
    done
    if [ -n "$blocked" ]; then echo "BLOCKED_STYLES $slug $revision$blocked"; fi
    ;;
inspect)
    need_slug
    "$PY_ACE" - "$root" "$revision" "$published" <<'PY'
import json, sys
from pathlib import Path
root, revision, published = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
run = root / f'{revision}-run'
print('PHASE_STATE ' + json.dumps({'source': (run / 'source-checks.json').is_file(), 'raw_source': (run / 'raw-source').exists(), 'finished': published.exists(), 'delivered': (published / 'checksums.json').is_file()}))
for path in sorted(run.glob('*.log')) + sorted(root.glob(f'*/{revision}/*.log')):
    content = path.read_text(errors='replace')
    if any(word in content for word in ('Traceback', 'Error', 'FAIL', 'killed', 'BLOCKED')):
        print('LOG', path)
        print('\n'.join(content.splitlines()[-12:]))
PY
    ;;
status)
    need_slug
    for style in $(styles_present); do
        f="$root/$style/$revision/picks.json"
        if [ -f "$f" ]; then
            "$PY_ACE" -c 'import json, sys; p = json.load(open(sys.argv[1])); print(sys.argv[2], p.get("status"), "main", p.get("picks_instr"), "backups", p.get("backups"))' "$f" "$style"
        else
            echo "$style no picks"
        fi
    done
    test -f "$published/checksums.json" && echo "published $published" || echo "not published"
    ;;
finish)
    need_slug; lock "$slug"
    test ! -e "$published" || { echo "$published exists: deliveries are final, make a new revision"; exit 65; }
    mkdir -p "$PUBLISHED/$slug"
    "$PY_ACE" "$tools/finish.py" "$root" "$revision" "$published" > "$run/finish.log" 2>&1 || { tail -n 20 "$run/finish.log"; rm -rf "$published"; exit 6; }
    tail -n 4 "$run/finish.log"
    ;;
deliver)
    need_slug; lock "$slug"
    test -d "$published" || { echo "no $published: run.sh finish first"; exit 66; }
    "$PY_ACE" "$tools/deliver.py" "$root" "$revision" "$published" > "$run/deliver.log" 2>&1 || { tail -n 20 "$run/deliver.log"; exit 6; }
    "$PY_ACE" "$tools/verify.py" "$published" > "$run/qa.log" 2>&1 || { cat "$run/qa.log"; exit 5; }
    mkdir -p "$published/evidence/run"
    cp "$run/deliver.log" "$run/qa.log" "$published/evidence/run/"
    seal "$published"
    cat "$run/qa.log"
    echo "DELIVERED $published"
    ;;
remix)
    need_slug
    parent="${3:?parent revision}"; new="${4:?new revision}"; shift 4
    reason="$*"; test -n "$reason" || { echo "remix needs a reason"; exit 64; }
    lock "$slug"
    out="$PUBLISHED/$slug/$new"
    test ! -e "$out" || { echo "$out exists"; exit 65; }
    mkdir -p "$root/$new-run"
    "$PY_ACE" "$tools/remix.py" "$root" "$parent" "$new" "$out" "$reason" > "$root/$new-run/finish.log" 2>&1 || { tail -n 30 "$root/$new-run/finish.log"; rm -rf "$out"; exit 6; }
    "$PY_ACE" "$tools/verify.py" "$out" > "$root/$new-run/qa.log" 2>&1 || { cat "$root/$new-run/qa.log"; exit 5; }
    mkdir -p "$out/evidence/run"
    cp "$root/$new-run/finish.log" "$root/$new-run/qa.log" "$out/evidence/run/"
    seal "$out"
    cat "$root/$new-run/qa.log"
    echo "DELIVERED $out"
    ;;
*) usage; exit 64 ;;
esac
