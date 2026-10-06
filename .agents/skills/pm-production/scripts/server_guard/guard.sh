#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../../../.." && pwd)"
ENV="$REPO/.claude/skills/video-generator/remote.env"
[ -f "$ENV" ] && source "$ENV"
REMOTE="${GUARD_REMOTE:-${VG_REMOTE:?set VG_REMOTE in $ENV}}"
KEY="${VG_KEY:-$HOME/.ssh/id_rsa}"
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=10 "$REMOTE")
START='systemctl --user is-active --quiet youtube-guard || systemd-run --user --unit=youtube-guard --collect -p MemoryMax=256M python3 ~/youtube-guard/guard.py >/dev/null 2>&1'
SLICE='S=~/.config/systemd/user/youtube.slice; [ -f $S ] || { mkdir -p ${S%/*} && printf "[Unit]\nDescription=youtube project: every skill shares this cap (CLAUDE.md)\n[Slice]\nCPUQuota=%s%%\nMemoryHigh=60%%\nMemoryMax=70%%\n" $(( $(nproc) * 60 )) > $S && systemctl --user daemon-reload; }'

case "${1:-status}" in
  install)
    "${SSH[@]}" "mkdir -p ~/youtube-guard"
    rsync -a -e "ssh -i $KEY -o BatchMode=yes" "$HERE/guard.py" "$REMOTE:youtube-guard/guard.py"
    "${SSH[@]}" "systemctl --user stop youtube-guard 2>/dev/null; $START; sleep 1; systemctl --user is-active youtube-guard"
    ;;
  status)
    "${SSH[@]}" "systemctl --user is-active youtube-guard || true; tail -n 3 ~/youtube-guard/guard.log 2>/dev/null; echo '-- kills:'; tail -n 5 ~/youtube-guard/kills.log 2>/dev/null || echo none"
    ;;
  log)
    "${SSH[@]}" "tail -n ${2:-30} ~/youtube-guard/guard.log"
    ;;
  kills)
    "${SSH[@]}" "cat ~/youtube-guard/kills.log 2>/dev/null || echo none"
    ;;
  run)
    shift
    "${SSH[@]}" "$START; $SLICE; systemd-run --user --scope --quiet --collect --slice=youtube.slice -p CPUQuota=2400% -- bash -c $(printf %q "$*")"
    ;;
  test)
    "${SSH[@]}" "$START; $SLICE; printf '{\"scope_ram_gb\": 2}' > ~/youtube-guard/guard.json; \
      (systemd-run --user --scope --quiet --collect --slice=youtube.slice -- python3 -c 'import time; b=bytearray(3*1024**3); b[::4096]=b\"x\"*len(b[::4096]); time.sleep(60)'; echo \"test job exit code: \$?\") ; \
      rm -f ~/youtube-guard/guard.json; tail -n 2 ~/youtube-guard/kills.log"
    ;;
  *)
    echo "usage: guard.sh install | status | log [N] | kills | run '<command>' | test" >&2
    exit 2
    ;;
esac
