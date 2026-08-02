#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export PORT="${PORT:-3001}"
LOG_FILE="/tmp/calendar-app.log"
PIP_LOG_FILE="/tmp/calendar-pip.log"

: > "$LOG_FILE"
: > "$PIP_LOG_FILE"

PYTHON_BIN="$(command -v python3 || true)"
if [ -z "$PYTHON_BIN" ]; then
  echo "python3 not found" | tee -a "$LOG_FILE"
  exit 1
fi

VENV_DIR="$SCRIPT_DIR/.venv"
echo "Using python: $PYTHON_BIN" | tee -a "$LOG_FILE"
"$PYTHON_BIN" -V 2>&1 | tee -a "$LOG_FILE"

if [ ! -x "$VENV_DIR/bin/python3" ]; then
  echo "Creating virtual environment" | tee -a "$LOG_FILE"
  "$PYTHON_BIN" -m venv "$VENV_DIR" >> "$LOG_FILE" 2>&1 || {
    echo "Failed to create virtual environment" | tee -a "$LOG_FILE"
    exit 1
  }
fi

VENV_PYTHON="$VENV_DIR/bin/python3"
echo "Using virtualenv python: $VENV_PYTHON" | tee -a "$LOG_FILE"
"$VENV_PYTHON" -m pip install --upgrade pip >> "$PIP_LOG_FILE" 2>&1 || true
"$VENV_PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt" >> "$PIP_LOG_FILE" 2>&1 || true

echo "Testing imports" | tee -a "$LOG_FILE"
"$VENV_PYTHON" -c "import flask, requests, dotenv; print('imports ok')" >> "$LOG_FILE" 2>&1 || true

echo "Starting app" | tee -a "$LOG_FILE"
exec "$VENV_PYTHON" "$SCRIPT_DIR/app.py" 2>&1 | tee -a "$LOG_FILE"
