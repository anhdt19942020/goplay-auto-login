#!/bin/bash
set -e

echo "Starting Xvfb..."
Xvfb :99 -screen 0 1280x720x24 -nolisten tcp &
export DISPLAY=:99
sleep 1

echo "Starting GoPlay API..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
