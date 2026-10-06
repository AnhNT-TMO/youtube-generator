#!/usr/bin/env bash
set -euo pipefail

PORT="${MUSE_CHROME_PORT:-9224}"
PROFILE_DIR="${MUSE_CHROME_PROFILE:-$HOME/.muse-chrome/profile}"
PROXY="${MUSE_CHROME_PROXY:-socks5://127.0.0.1:1080}"
URL="${1:-https://ipinfo.io/json}"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

[ "$PROXY" = "none" ] && PROXY=""

if [ -n "$PROXY" ]; then
  HOSTPORT="${PROXY#*://}"
  PROXY_HOST="${HOSTPORT%:*}"
  PROXY_PORT="${HOSTPORT##*:}"
  if ! nc -z "$PROXY_HOST" "$PROXY_PORT" >/dev/null 2>&1; then
    echo "Proxy ${PROXY} chưa chạy. Bật: ~/.local/bin/us-proxy start (hoặc MUSE_CHROME_PROXY=none để đi mạng thường / extension VPN)" >&2
    exit 1
  fi
fi

if curl -s "http://127.0.0.1:${PORT}/json/version" >/dev/null 2>&1; then
  RUNNING_ARGS="$(ps -Ao args | grep -F -- "--remote-debugging-port=${PORT}" | grep -v grep | head -1 || true)"
  if [ -n "$PROXY" ] && ! grep -qF -- "--proxy-server=${PROXY}" <<<"$RUNNING_ARGS"; then
    echo "muse-chrome đang chạy KHÔNG qua proxy ${PROXY}. Đóng hẳn Chrome muse (Cmd+Q) rồi chạy lại lệnh này." >&2
    exit 1
  fi
  curl -s -X PUT "http://127.0.0.1:${PORT}/json/new?${URL}" >/dev/null
  echo "muse-chrome đã chạy trên cổng ${PORT}${PROXY:+ (proxy: ${PROXY})}"
  exit 0
fi

EXTRA_ARGS=()
if [ -n "$PROXY" ]; then
  EXTRA_ARGS+=("--proxy-server=${PROXY}" "--force-webrtc-ip-handling-policy=disable_non_proxied_udp")
fi

mkdir -p "$PROFILE_DIR"
TZ="${MUSE_CHROME_TZ:-America/Los_Angeles}" "$CHROME" \
  --remote-debugging-port="$PORT" \
  --user-data-dir="$PROFILE_DIR" \
  --lang=en-US \
  --no-first-run \
  --no-default-browser-check \
  ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"} \
  "$URL" >/dev/null 2>&1 &

for _ in $(seq 1 20); do
  if curl -s "http://127.0.0.1:${PORT}/json/version" >/dev/null 2>&1; then
    echo "muse-chrome sẵn sàng trên cổng ${PORT} (profile: ${PROFILE_DIR}${PROXY:+, proxy: ${PROXY}})"
    exit 0
  fi
  sleep 0.5
done
echo "Không kết nối được Chrome trên cổng ${PORT}" >&2
exit 1
