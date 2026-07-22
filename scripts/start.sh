#!/bin/sh
set -e

cd /app/apps/backend
uvicorn src.main:app --host 0.0.0.0 --port 18765 &

exec nginx -g "daemon off;"
