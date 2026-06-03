#!/bin/sh
set -e

# Install dependencies if in development mode
if [ "$APP_ENV" != "production" ] && [ "$APP_ENV" != "prod" ]; then
  echo "Installing Python dependencies (Development mode)..."
  pip install --no-cache-dir -r requirements.txt
fi

# Run custom command if provided
if [ $# -gt 0 ]; then
  echo "Running custom command: $@"
  exec "$@"
fi

if [ "$APP_ENV" = "production" ] || [ "$APP_ENV" = "prod" ]; then
  echo "Starting FastAPI backend in PRODUCTION mode..."
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000
else
  echo "Starting FastAPI backend in DEVELOPMENT mode..."
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi
