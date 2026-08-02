#!/bin/bash
set -euo pipefail

export DISPLAY=:0
export XAUTHORITY=/home/pi/.Xauthority

sleep 10

# Boot-time readiness checks
# Wait until system uptime passes a small threshold so services and desktop settle
UPTIME_THRESHOLD=60
UPTIME_NOW=$(awk '{print int($1)}' /proc/uptime 2>/dev/null || echo 0)
if [ "$UPTIME_NOW" -lt "$UPTIME_THRESHOLD" ]; then
  echo "$(date) uptime $UPTIME_NOW < $UPTIME_THRESHOLD; waiting..." >> /tmp/calendar-kiosk.log
  while [ "$(awk '{print int($1)}' /proc/uptime 2>/dev/null || echo 0)" -lt "$UPTIME_THRESHOLD" ]; do
    sleep 1
  done
  echo "$(date) uptime threshold reached" >> /tmp/calendar-kiosk.log
fi

# Wait for an X server to be present before attempting to start the browser
for i in {1..30}; do
  if pgrep -x Xorg >/dev/null 2>&1 || pgrep -x X >/dev/null 2>&1; then
    echo "$(date) X server detected" >> /tmp/calendar-kiosk.log
    break
  fi
  echo "$(date) waiting for X server" >> /tmp/calendar-kiosk.log
  sleep 2
done


echo "$(date) kiosk start" >> /tmp/calendar-kiosk.log
if [ -z "$DISPLAY" ]; then
  export DISPLAY=:0
fi
if [ -z "$XAUTHORITY" ]; then
  export XAUTHORITY=/home/pi/.Xauthority
fi

echo "$(date) DISPLAY=$DISPLAY XAUTHORITY=$XAUTHORITY" >> /tmp/calendar-kiosk.log
ls -l "$XAUTHORITY" >> /tmp/calendar-kiosk.log 2>&1 || true

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

PROFILE_DIR="/tmp/calendar-chrome-profile"
mkdir -p "$PROFILE_DIR"

echo "$(date) found browser: $BROWSER" >> /tmp/calendar-kiosk.log

echo "$(date) launching browser: $BROWSER --noerrdialogs --disable-infobars --kiosk --start-maximized --password-store=basic --no-first-run --no-default-browser-check --user-data-dir=$PROFILE_DIR http://localhost:3001" >> /tmp/calendar-kiosk.log
"$BROWSER" \
  --noerrdialogs \
  --disable-infobars \
  --kiosk \
  --start-maximized \
  --password-store=basic \
  --no-first-run \
  --no-default-browser-check \
  --user-data-dir="$PROFILE_DIR" \
  http://localhost:3001 >>/tmp/calendar-kiosk.log 2>&1 &
BROWSER_PID=$!

echo "$(date) browser pid=$BROWSER_PID" >> /tmp/calendar-kiosk.log
sleep 3
if ! kill -0 "$BROWSER_PID" 2>/dev/null; then
  echo "$(date) browser process died immediately" >> /tmp/calendar-kiosk.log
fi
