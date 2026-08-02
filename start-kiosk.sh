#!/bin/bash
set -euo pipefail

export DISPLAY=:0
export XAUTHORITY=/home/pi/.Xauthority

sleep 10

echo "$(date) kiosk start" >> /tmp/calendar-kiosk.log
echo "$(date) DISPLAY=$DISPLAY XAUTHORITY=$XAUTHORITY" >> /tmp/calendar-kiosk.log

for i in {1..30}; do
  if curl -sf http://127.0.0.1:3001 >/dev/null 2>&1; then
    echo "$(date) server is reachable" >> /tmp/calendar-kiosk.log
    break
  fi
  echo "$(date) waiting for server" >> /tmp/calendar-kiosk.log
  sleep 2
done

if ! curl -sf http://127.0.0.1:3001 >/dev/null 2>&1; then
  echo "$(date) server never became reachable" >> /tmp/calendar-kiosk.log
  exit 1
fi

BROWSER=""
for candidate in $(command -v chromium chromium-browser google-chrome firefox 2>/dev/null); do
  if [ -x "$candidate" ]; then
    BROWSER="$candidate"
    break
  fi
done

if [ -z "$BROWSER" ]; then
  echo "$(date) no supported browser found" >> /tmp/calendar-kiosk.log
  exit 1
fi

echo "$(date) found browser: $BROWSER" >> /tmp/calendar-kiosk.log

echo "$(date) launching browser: $BROWSER --noerrdialogs --disable-infobars --kiosk --start-maximized http://localhost:3001" >> /tmp/calendar-kiosk.log
"$BROWSER" \
  --noerrdialogs \
  --disable-infobars \
  --kiosk \
  --start-maximized \
  --password-store=basic \
  --no-first-run \
  --no-default-browser-check \
  http://localhost:3001 >>/tmp/calendar-kiosk.log 2>&1 &
BROWSER_PID=$!

echo "$(date) browser pid=$BROWSER_PID" >> /tmp/calendar-kiosk.log
sleep 3
if ! kill -0 "$BROWSER_PID" 2>/dev/null; then
  echo "$(date) browser process died immediately" >> /tmp/calendar-kiosk.log
fi
