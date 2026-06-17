#!/bin/sh
set -e

# Install dependencies if in development mode
if [ "$APP_ENV" != "production" ] && [ "$APP_ENV" != "prod" ] && [ "$APP_ENV" != "staging" ] && [ "$APP_ENV" != "test" ]; then
  echo "Installing Python dependencies (Development mode)..."
  pip install --no-cache-dir -r requirements.txt
fi

echo "Starting scheduler worker..."
exec python -m app.scheduler
