#!/usr/bin/env bash
set -euo pipefail

SK="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$SK/../../.." && pwd)"
[ -f "$SK/remote.env" ] && source "$SK/remote.env"
: "${QC_REMOTE:?set QC_REMOTE=user@host in $SK/remote.env (mẫu: remote.env.example)}"
HOST="$QC_REMOTE"
KEY="${QC_KEY:-$HOME/.ssh/id_rsa}"
RDIR="${QC_DIR:-youtube-qc}"
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=10 "$HOST")
RSH="ssh -i $KEY -o BatchMode=yes -o ConnectTimeout=10"
LIMIT='G=~/youtube-guard/guard.py; if [ -f $G ]; then systemctl --user is-active --quiet youtube-guard || systemd-run --user --unit=youtube-guard --collect -p MemoryMax=256M python3 $G >/dev/null 2>&1; else echo "WARNING: youtube-guard not installed on the server (pm-production/scripts/server_guard/guard.sh install)" >&2; fi; S=~/.config/systemd/user/youtube.slice; [ -f $S ] || { mkdir -p ${S%/*} && printf "[Unit]\nDescription=youtube project: every skill shares this cap (CLAUDE.md)\n[Slice]\nCPUQuota=%s%%\nMemoryHigh=60%%\nMemoryMax=70%%\n" $(( $(nproc) * 60 )) > $S && systemctl --user daemon-reload; }; systemd-run --user --scope --quiet --collect --slice=youtube.slice -- bash -c'

case "${1:-}" in
  push)
    rsync -aW --files-from=- -e "$RSH" "$REPO/" "$HOST:$RDIR/"
    rsync -aW --delete -e "$RSH" --include 'tracks/***' --exclude '*' "$REPO/$2/" "$HOST:$RDIR/$2/"
    ;;
  exec) "${SSH[@]}" "$LIMIT $(printf %q "cd $RDIR && $2")" ;;
  pull)
    N="$(basename "$2")"
    rsync -aW -e "$RSH" --include 'assembly.json' --include 'assembly.md' --include 'audio/' --include 'audio/master/' \
      --include "audio/master/$N.wav" --include "audio/master/$N.mp3" --exclude '*' "$HOST:$RDIR/$2/" "$REPO/$2/"
    ;;
  *) echo "usage: remote.sh push <album> (repo-relative file list on stdin) | exec '<cmd>' | pull <album>" >&2; exit 2 ;;
esac
