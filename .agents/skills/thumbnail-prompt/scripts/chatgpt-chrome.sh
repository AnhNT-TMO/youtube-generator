#!/usr/bin/env bash
set -euo pipefail

PORT="${CHATGPT_CHROME_PORT:-9223}"
PROFILE_DIR="${CHATGPT_CHROME_PROFILE:-$HOME/.chatgpt-chrome/profile}"
URL="${1:-https://chatgpt.com/}"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

if curl -s "http://127.0.0.1:${PORT}/json/version" >/dev/null 2>&1; then
  curl -s -X PUT "http://127.0.0.1:${PORT}/json/new?${URL}" >/dev/null
  echo "chatgpt-chrome đã chạy trên cổng ${PORT}"
  exit 0
fi

mkdir -p "$PROFILE_DIR"
"$CHROME" \
  --remote-debugging-port="$PORT" \
  --user-data-dir="$PROFILE_DIR" \
  --no-first-run \
  --no-default-browser-check \
  "$URL" >/dev/null 2>&1 &

for _ in $(seq 1 20); do
  if curl -s "http://127.0.0.1:${PORT}/json/version" >/dev/null 2>&1; then
    echo "chatgpt-chrome sẵn sàng trên cổng ${PORT} (profile: ${PROFILE_DIR})"
    exit 0
  fi
  sleep 0.5
done
echo "Không kết nối được Chrome trên cổng ${PORT}" >&2
exit 1
