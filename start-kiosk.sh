#!/bin/bash
set -euo pipefail

export DISPLAY=:0
export XAUTHORITY=/home/pi/.Xauthority

sleep 10

for i in {1..30}; do
  if curl -sf http://127.0.0.1:3001 >/dev/null 2>&1; then
    break
  fi
  echo "$(date) waiting for server" >> /tmp/calendar-kiosk.log
  sleep 2
done

BROWSER=""
for candidate in /usr/bin/chromium /usr/bin/chromium-browser /usr/bin/google-chrome /usr/bin/firefox; do
  if [ -x "$candidate" ]; then
    BROWSER="$candidate"
    break
  fi
done

if [ -z "$BROWSER" ]; then
  echo "$(date) no supported browser found" >> /tmp/calendar-kiosk.log
  exit 1
fi

"$BROWSER" \
  --noerrdialogs \
  --disable-infobars \
  --kiosk \
  --start-maximized \
  http://localhost:3001 >>/tmp/calendar-kiosk.log 2>&1 &
