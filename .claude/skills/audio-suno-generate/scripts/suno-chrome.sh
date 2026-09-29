#!/usr/bin/env bash
set -euo pipefail

PORT="${SUNO_CHROME_PORT:-9222}"
PROFILE_DIR="${SUNO_CHROME_PROFILE:-$HOME/.suno-chrome/profile}"
URL="${1:-https://suno.com/create}"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

if curl -s "http://127.0.0.1:${PORT}/json/version" >/dev/null 2>&1; then
  curl -s -X PUT "http://127.0.0.1:${PORT}/json/new?${URL}" >/dev/null
  echo "suno-chrome đã chạy trên cổng ${PORT}"
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
    echo "suno-chrome sẵn sàng trên cổng ${PORT} (profile: ${PROFILE_DIR})"
    exit 0
  fi
  sleep 0.5
done
echo "Không kết nối được Chrome trên cổng ${PORT}" >&2
exit 1
